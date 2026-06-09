from pathlib import Path

import faiss
import pyarrow.parquet as pq
from fastapi import FastAPI
from fastapi.testclient import TestClient

from molecular_similarity.company_onboarding import create_onboarding_router
from molecular_similarity.compliance_config import CompanyComplianceConfig
from molecular_similarity.ra_decision_router import RADecisionRouter
from molecular_similarity.ra_response_schema import (
    RADecisionResponse,
    RAThresholdSnapshot,
    build_ra_decision_response,
)


MOCK_COMPOUND_SMILES = [
    "CCO",
    "CCN",
    "CCC",
    "CCCl",
    "CCBr",
    "CC(=O)O",
    "c1ccccc1",
    "Cc1ccccc1",
    "Oc1ccccc1",
    "Nc1ccccc1",
    "CCOC",
    "CCS",
    "CC(C)O",
    "CC(C)N",
    "CC(C)C",
    "CC(=O)N",
    "COC",
    "CN(C)N=O",
    "C1OC1",
    "CCN(CC)CC",
]


def _mock_company_config() -> CompanyComplianceConfig:
    return CompanyComplianceConfig.model_validate(
        {
            "schema_version": "1.0",
            "company_id": "mock_company",
            "company_name": "Mock Company",
            "effective_date": "2026-06-09",
            "owner": "Mock RA",
            "jurisdictions": ["FDA", "EMA"],
            "therapeutic_areas": ["Oncology"],
            "similarity_thresholds": {
                "candidate_match": 0.65,
                "high_confidence_match": 0.85,
                "manual_review_below": 0.55,
            },
            "structural_alerts": {
                "alerts_nitrosamine": {
                    "enabled": True,
                    "default_action": "block",
                    "severity": "critical",
                    "rationale": "Mock company blocks nitrosamine-like alerts.",
                }
            },
        }
    )


def _compound_library_csv() -> bytes:
    lines = ["compound_id,name,smiles"]
    for index, smiles in enumerate(MOCK_COMPOUND_SMILES, start=1):
        lines.append(f"MC-{index:03d},Mock Compound {index},{smiles}")
    return ("\n".join(lines) + "\n").encode()


def _ra_history_csv() -> bytes:
    lines = ["compound_id,smiles,ra_outcome,decision_date,jurisdiction,notes"]
    for index, smiles in enumerate(MOCK_COMPOUND_SMILES[:10], start=1):
        outcome = "approved" if index % 2 else "review_required"
        lines.append(
            f"MC-{index:03d},{smiles},{outcome},2026-01-{index:02d},FDA,"
            f"Mock precedent {index}"
        )
    return ("\n".join(lines) + "\n").encode()


def test_mock_company_end_to_end_onboarding_and_ra_response(
    tmp_path: Path,
) -> None:
    app = FastAPI()
    index_root = tmp_path / "indexes"
    history_root = tmp_path / "history"
    app.include_router(create_onboarding_router(index_root=index_root, history_root=history_root))
    client = TestClient(app)

    library_response = client.post(
        "/onboarding/library",
        data={"company_id": "Mock Company"},
        files={"file": ("mock_library.csv", _compound_library_csv(), "text/csv")},
    )
    history_response = client.post(
        "/onboarding/ra-history",
        data={"company_id": "Mock Company"},
        files={"file": ("mock_ra_history.csv", _ra_history_csv(), "text/csv")},
    )

    assert library_response.status_code == 200
    assert history_response.status_code == 200
    library_payload = library_response.json()
    history_payload = history_response.json()
    assert library_payload["company_id"] == "mock_company"
    assert library_payload["compound_count"] == 20
    assert faiss.read_index(library_payload["index_path"]).ntotal == 20
    assert history_payload["history_count"] == 10
    assert pq.read_table(history_payload["history_path"]).num_rows == 10

    company_config = _mock_company_config()
    decision = RADecisionRouter(company_config).route(
        model_score=0.93,
        alert_flags={"alerts_nitrosamine": True},
    )
    thresholds = RAThresholdSnapshot(
        candidate_match=company_config.similarity_thresholds.candidate_match,
        high_confidence_match=company_config.similarity_thresholds.high_confidence_match,
        manual_review_below=company_config.similarity_thresholds.manual_review_below,
    )
    response = build_ra_decision_response(
        company_id=company_config.company_id,
        input_compound={
            "chembl_id": "MOCK-QUERY",
            "name": "Mock Query",
            "smiles": "CN(C)N=O",
        },
        decision=decision,
        thresholds=thresholds,
        alert_summaries=[
            {
                "alert_name": "alerts_nitrosamine",
                "triggered": True,
                "action": "block",
                "severity": "critical",
                "rationale": "Mock company blocks nitrosamine-like alerts.",
            }
        ],
        top_analog={
            "chembl_id": "MC-001",
            "name": "Mock Compound 1",
            "max_phase": 4.0,
            "approval_year": 2026,
        },
        audit_trail=[
            {"step": "library_upload", "message": "Uploaded 20 mock compounds."},
            {"step": "history_upload", "message": "Uploaded 10 mock RA decisions."},
            {"step": "router", "message": "Alert escalation overrode model score."},
        ],
        ra_justification={
            "summary": decision.reason,
            "score_rationale": "Score was high, but deterministic alert escalation applies.",
            "alert_rationale": "alerts_nitrosamine is configured as critical block.",
            "precedent_rationale": "Mock approved analog MC-001 was attached as context.",
            "history_rationale": "10 company RA decisions are available for precedent lookup.",
        },
    )

    validated_response = RADecisionResponse.model_validate(response.model_dump())
    assert validated_response.company_id == "mock_company"
    assert validated_response.decision == "block"
    assert validated_response.reason.startswith("Alert escalation override")
    assert validated_response.score.confidence_band == "high"
    assert validated_response.ra_justification.alert_rationale == (
        "alerts_nitrosamine is configured as critical block."
    )
    assert validated_response.ra_justification.history_rationale == (
        "10 company RA decisions are available for precedent lookup."
    )
    assert validated_response.top_analog is not None
    assert validated_response.top_analog.chembl_id == "MC-001"
    assert len(validated_response.audit_trail) == 3
