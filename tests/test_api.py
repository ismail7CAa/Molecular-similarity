import json
from pathlib import Path

from fastapi.testclient import TestClient

from molecular_similarity.api import create_app


def _write_company_config(config_root: Path) -> None:
    config_root.mkdir()
    (config_root / "mock_company.json").write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "company_id": "mock_company",
                "company_name": "Mock Company",
                "effective_date": "2026-06-09",
                "owner": "Regulatory Affairs",
                "jurisdictions": ["FDA", "EMA", "ICH"],
                "therapeutic_areas": ["Oncology"],
                "similarity_thresholds": {
                    "candidate_match": 0.65,
                    "high_confidence_match": 0.85,
                    "manual_review_below": 0.55,
                },
                "outcome_thresholds": {
                    "approval_likelihood_review": 0.5,
                    "safety_risk_review": 0.35,
                    "safety_risk_block": 0.7,
                },
                "phase_policy": {
                    "minimum_preferred_max_phase": 2.0,
                    "require_approved_reference": False,
                    "approved_reference_min_phase": 4.0,
                },
                "structural_alerts": {
                    "alerts_nitrosamine": {
                        "enabled": True,
                        "default_action": "block",
                        "severity": "critical",
                        "rationale": "Nitrosamine alert requires immediate review.",
                    }
                },
                "rules": [],
            }
        )
    )


def test_production_api_predict_returns_ra_decision_and_audit_log(
    tmp_path: Path,
    monkeypatch,
) -> None:
    config_root = tmp_path / "configs"
    audit_root = tmp_path / "audit"
    _write_company_config(config_root)
    monkeypatch.setenv("COMPANY_CONFIG_ROOT", str(config_root))
    monkeypatch.setenv("COMPANY_INDEX_ROOT", str(tmp_path / "indexes"))
    monkeypatch.setenv("COMPANY_HISTORY_ROOT", str(tmp_path / "history"))
    monkeypatch.setenv("COMPANY_AUDIT_ROOT", str(audit_root))

    client = TestClient(create_app())

    health_response = client.get("/health")
    assert health_response.status_code == 200
    assert health_response.json() == {"status": "ok"}

    response = client.post(
        "/predict",
        json={
            "company_id": "mock_company",
            "input_compound": {
                "chembl_id": "CHEMBL999",
                "name": "Input candidate",
                "smiles": "CN=O",
            },
            "model_score": 0.93,
            "alert_flags": {"alerts_nitrosamine": True},
            "top_analog": {
                "chembl_id": "CHEMBL25",
                "name": "Approved analog",
                "max_phase": 4.0,
                "approval_year": 2018,
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["company_id"] == "mock_company"
    assert payload["decision"] == "block"
    assert payload["score"]["confidence_band"] == "high"
    assert payload["top_analog"]["chembl_id"] == "CHEMBL25"
    assert payload["ra_justification"]["alert_rationale"] == (
        "Triggered configured alerts: alerts_nitrosamine"
    )
    assert payload["triggered_alerts"][0]["alert_name"] == "alerts_nitrosamine"

    log_path = audit_root / "mock_company" / "log.jsonl"
    assert log_path.exists()
    audit_entry = json.loads(log_path.read_text().splitlines()[0])
    assert audit_entry["path"] == "/predict"
    assert audit_entry["status_code"] == 200
    assert audit_entry["response"]["body"]["decision"] == "block"


def test_production_api_rejects_missing_company_config(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("COMPANY_CONFIG_ROOT", str(tmp_path / "configs"))
    monkeypatch.setenv("COMPANY_AUDIT_ROOT", str(tmp_path / "audit"))

    client = TestClient(create_app())
    response = client.post(
        "/predict",
        json={
            "company_id": "unknown_company",
            "input_compound": {"chembl_id": "CHEMBL1", "name": "", "smiles": "CCO"},
            "model_score": 0.5,
        },
    )

    assert response.status_code == 404
