from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from molecular_similarity.tenant_namespace import company_namespace_path, safe_company_id


DEFAULT_AUDIT_ROOT = Path("audit")


class AuditLogEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    audit_id: str = Field(min_length=1)
    logged_at: datetime
    company_id: str = Field(min_length=1)
    method: str
    path: str
    status_code: int
    request: dict[str, object]
    response: dict[str, object]


def _decode_json_body(body: bytes) -> object:
    if not body:
        return None
    try:
        return json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return {"raw_body_size": len(body)}


def _header_value(scope: Scope, header_name: str) -> str | None:
    expected = header_name.lower().encode("latin-1")
    for key, value in scope.get("headers", []):
        if key.lower() == expected:
            return value.decode("latin-1")
    return None


def _company_id_from_context(
    scope: Scope,
    request_body: object,
    response_body: object,
) -> str:
    if isinstance(response_body, dict) and response_body.get("company_id"):
        return safe_company_id(response_body["company_id"])
    if isinstance(request_body, dict) and request_body.get("company_id"):
        return safe_company_id(request_body["company_id"])
    header_company_id = _header_value(scope, "x-company-id")
    if header_company_id:
        return safe_company_id(header_company_id)
    return "unknown"


def append_audit_log(entry: AuditLogEntry, audit_root: Path = DEFAULT_AUDIT_ROOT) -> Path:
    audit_dir = company_namespace_path(audit_root, entry.company_id)
    audit_dir.mkdir(parents=True, exist_ok=True)
    audit_path = audit_dir / "log.jsonl"
    with audit_path.open("a", encoding="utf-8") as handle:
        handle.write(entry.model_dump_json() + "\n")
    return audit_path


class AuditLogMiddleware:
    """Append-only JSONL audit middleware for GxP-sensitive prediction calls."""

    def __init__(
        self,
        app: ASGIApp,
        audit_root: Path | str = DEFAULT_AUDIT_ROOT,
        audited_paths: tuple[str, ...] = ("/predict",),
    ):
        self.app = app
        self.audit_root = Path(audit_root)
        self.audited_paths = audited_paths

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or not self._should_audit(str(scope.get("path", ""))):
            await self.app(scope, receive, send)
            return

        request_messages = await self._read_request_messages(receive)
        request_body_bytes = b"".join(
            message.get("body", b"")
            for message in request_messages
            if message["type"] == "http.request"
        )
        request_body = _decode_json_body(request_body_bytes)
        replay_receive = self._replay_receive(request_messages)

        response_messages: list[Message] = []

        async def capture_send(message: Message) -> None:
            response_messages.append(message)

        await self.app(scope, replay_receive, capture_send)

        status_code = self._status_code(response_messages)
        response_body_bytes = b"".join(
            message.get("body", b"")
            for message in response_messages
            if message["type"] == "http.response.body"
        )
        response_body = _decode_json_body(response_body_bytes)
        company_id = _company_id_from_context(scope, request_body, response_body)
        entry = AuditLogEntry(
            audit_id=str(uuid4()),
            logged_at=datetime.now(UTC),
            company_id=company_id,
            method=str(scope.get("method", "")),
            path=str(scope.get("path", "")),
            status_code=status_code,
            request={
                "query_string": scope.get("query_string", b"").decode("latin-1"),
                "body": request_body,
            },
            response={
                "body": response_body,
            },
        )
        append_audit_log(entry, self.audit_root)

        for message in response_messages:
            await send(message)

    def _should_audit(self, path: str) -> bool:
        return any(
            path == audited_path or path.startswith(f"{audited_path}/")
            for audited_path in self.audited_paths
        )

    @staticmethod
    async def _read_request_messages(receive: Receive) -> list[Message]:
        messages: list[Message] = []
        while True:
            message = await receive()
            messages.append(message)
            if message["type"] != "http.request" or not message.get("more_body", False):
                break
        return messages

    @staticmethod
    def _replay_receive(messages: list[Message]) -> Receive:
        pending_messages = list(messages)

        async def receive() -> Message:
            if pending_messages:
                return pending_messages.pop(0)
            return {"type": "http.request", "body": b"", "more_body": False}

        return receive

    @staticmethod
    def _status_code(messages: list[Message]) -> int:
        for message in messages:
            if message["type"] == "http.response.start":
                return int(message.get("status", 0))
        return 0
