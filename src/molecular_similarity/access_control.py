from __future__ import annotations

import hashlib
import hmac
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fastapi import HTTPException, Request, status
from starlette.datastructures import FormData

from molecular_similarity.tenant_namespace import safe_company_id


DEFAULT_API_KEY_HEADER = "X-API-Key"


@dataclass(frozen=True)
class APIKeyPrincipal:
    key_id: str
    company_ids: frozenset[str]
    scopes: frozenset[str]


@dataclass(frozen=True)
class APIKeyRecord:
    key_id: str
    key_sha256: str
    company_ids: frozenset[str]
    scopes: frozenset[str]

    def matches(self, api_key: str) -> bool:
        candidate_hash = hashlib.sha256(api_key.encode("utf-8")).hexdigest()
        return hmac.compare_digest(candidate_hash, self.key_sha256)

    def to_principal(self) -> APIKeyPrincipal:
        return APIKeyPrincipal(
            key_id=self.key_id,
            company_ids=self.company_ids,
            scopes=self.scopes,
        )


class APIKeyAccessControl:
    def __init__(self, records: list[APIKeyRecord], header_name: str = DEFAULT_API_KEY_HEADER):
        self.records = records
        self.header_name = header_name

    @classmethod
    def from_environment(cls) -> APIKeyAccessControl:
        header_name = os.environ.get("API_KEY_HEADER", DEFAULT_API_KEY_HEADER)
        raw_config = os.environ.get("API_KEYS_JSON")
        config_path = os.environ.get("API_KEYS_FILE")
        if raw_config is None and config_path and Path(config_path).exists():
            raw_config = Path(config_path).read_text()
        if raw_config is None:
            return cls(records=[], header_name=header_name)
        return cls.from_mapping(json.loads(raw_config), header_name=header_name)

    @classmethod
    def from_mapping(
        cls,
        raw_records: dict[str, Any],
        header_name: str = DEFAULT_API_KEY_HEADER,
    ) -> APIKeyAccessControl:
        records: list[APIKeyRecord] = []
        for key_id, raw_record in raw_records.items():
            if not isinstance(raw_record, dict):
                raise ValueError("API key records must be JSON objects")
            key_sha256 = raw_record.get("key_sha256")
            plaintext_key = raw_record.get("key")
            if key_sha256 is None and plaintext_key is not None:
                key_sha256 = hashlib.sha256(str(plaintext_key).encode("utf-8")).hexdigest()
            if not key_sha256:
                raise ValueError(f"API key record {key_id!r} requires key_sha256 or key")

            company_ids = raw_record.get("company_ids") or []
            scopes = raw_record.get("scopes") or []
            records.append(
                APIKeyRecord(
                    key_id=str(key_id),
                    key_sha256=str(key_sha256),
                    company_ids=frozenset(
                        "*"
                        if str(company_id).strip() == "*"
                        else safe_company_id(company_id)
                        for company_id in company_ids
                    ),
                    scopes=frozenset(str(scope) for scope in scopes),
                )
            )
        return cls(records=records, header_name=header_name)

    def require(self, scope: str):
        async def dependency(request: Request) -> APIKeyPrincipal:
            principal = await self.authenticate(request)
            if scope not in principal.scopes and "*" not in principal.scopes:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"API key is missing required scope: {scope}",
                )

            requested_company_id = await company_id_from_request(request)
            if requested_company_id is not None:
                normalized_company_id = safe_company_id(requested_company_id)
                allowed_companies = principal.company_ids
                if "*" not in allowed_companies and normalized_company_id not in allowed_companies:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="API key is not authorized for this company_id",
                    )
            return principal

        return dependency

    async def authenticate(self, request: Request) -> APIKeyPrincipal:
        api_key = request.headers.get(self.header_name)
        if not self.records:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="API access control is not configured",
            )
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Missing {self.header_name} header",
            )
        for record in self.records:
            if record.matches(api_key):
                return record.to_principal()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )


async def company_id_from_request(request: Request) -> str | None:
    if request.method in {"GET", "HEAD", "OPTIONS"}:
        company_id = request.query_params.get("company_id")
        return company_id

    content_type = request.headers.get("content-type", "")
    if "multipart/form-data" in content_type or "application/x-www-form-urlencoded" in content_type:
        form = await request.form()
        return _company_id_from_form(form)

    try:
        body = await request.json()
    except json.JSONDecodeError:
        return None
    except Exception:
        return None

    if isinstance(body, dict) and body.get("company_id") is not None:
        return str(body["company_id"])
    return None


def _company_id_from_form(form: FormData) -> str | None:
    value = form.get("company_id")
    if value is None:
        return None
    return str(value)
