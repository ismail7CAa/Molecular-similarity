import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from molecular_similarity.audit_middleware import AuditLogMiddleware


def _create_app(audit_root: Path) -> FastAPI:
    app = FastAPI()
    app.add_middleware(
        AuditLogMiddleware,
        audit_root=audit_root,
        audited_paths=("/predict",),
    )

    @app.post("/predict")
    def predict(payload: dict[str, object]) -> dict[str, object]:
        return {
            "schema_version": "1.0",
            "company_id": payload["company_id"],
            "decision": "review",
            "reason": "Example deterministic response.",
            "score": {"model_score": 0.62, "confidence_band": "low"},
        }

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


def test_audit_middleware_appends_jsonl_before_returning_response(
    tmp_path: Path,
) -> None:
    audit_root = tmp_path / "audit"
    client = TestClient(_create_app(audit_root))

    response = client.post(
        "/predict",
        json={
            "company_id": "Example Pharma",
            "chembl_id": "CHEMBL123",
        },
    )

    assert response.status_code == 200
    log_path = audit_root / "example_pharma" / "log.jsonl"
    assert log_path.exists()
    lines = log_path.read_text().splitlines()
    assert len(lines) == 1

    entry = json.loads(lines[0])
    assert entry["company_id"] == "example_pharma"
    assert entry["method"] == "POST"
    assert entry["path"] == "/predict"
    assert entry["status_code"] == 200
    assert entry["request"]["body"]["chembl_id"] == "CHEMBL123"
    assert entry["response"]["body"]["decision"] == "review"


def test_audit_middleware_is_append_only(
    tmp_path: Path,
) -> None:
    audit_root = tmp_path / "audit"
    client = TestClient(_create_app(audit_root))

    client.post("/predict", json={"company_id": "example_pharma", "chembl_id": "CHEMBL1"})
    client.post("/predict", json={"company_id": "example_pharma", "chembl_id": "CHEMBL2"})

    log_path = audit_root / "example_pharma" / "log.jsonl"
    lines = [json.loads(line) for line in log_path.read_text().splitlines()]
    assert len(lines) == 2
    assert lines[0]["request"]["body"]["chembl_id"] == "CHEMBL1"
    assert lines[1]["request"]["body"]["chembl_id"] == "CHEMBL2"
    assert lines[0]["audit_id"] != lines[1]["audit_id"]


def test_audit_middleware_ignores_non_audited_paths(
    tmp_path: Path,
) -> None:
    audit_root = tmp_path / "audit"
    client = TestClient(_create_app(audit_root))

    response = client.get("/health")

    assert response.status_code == 200
    assert not audit_root.exists()


def test_audit_middleware_sanitizes_company_namespace(
    tmp_path: Path,
) -> None:
    audit_root = tmp_path / "audit"
    client = TestClient(_create_app(audit_root))

    response = client.post(
        "/predict",
        json={
            "company_id": "../Other Company",
            "chembl_id": "CHEMBL1",
        },
    )

    assert response.status_code == 200
    assert (audit_root / "other_company" / "log.jsonl").exists()
    assert not (tmp_path / "Other Company").exists()
