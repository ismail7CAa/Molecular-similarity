import pytest
from pydantic import ValidationError

from molecular_similarity.ra_decision_router import RADecision
from molecular_similarity.ra_response_schema import (
    RADecisionResponse,
    RAThresholdSnapshot,
    build_ra_decision_response,
)


def test_build_ra_decision_response_creates_auditable_object() -> None:
    response = build_ra_decision_response(
        company_id="example_pharma",
        input_compound={
            "chembl_id": "CHEMBL123",
            "name": "Query Compound",
            "smiles": "CCO",
        },
        decision=RADecision(
            decision="block",
            reason="Alert escalation override: alerts_nitrosamine triggered critical block.",
            model_score=0.98,
            triggered_alerts=["alerts_nitrosamine"],
        ),
        thresholds=RAThresholdSnapshot(
            candidate_match=0.65,
            high_confidence_match=0.85,
            manual_review_below=0.55,
        ),
        alert_summaries=[
            {
                "alert_name": "alerts_nitrosamine",
                "triggered": True,
                "action": "block",
                "severity": "critical",
                "rationale": "Nitrosamine alert requires immediate review.",
            }
        ],
        top_analog={
            "chembl_id": "CHEMBL25",
            "name": "Approved Analog",
            "max_phase": 4.0,
            "approval_year": 2011,
        },
        audit_trail=[
            {
                "step": "router",
                "message": "Alert escalation overrode model score.",
            }
        ],
    )

    assert response.decision == "block"
    assert response.score.model_score == 0.98
    assert response.score.confidence_band == "high"
    assert response.top_analog is not None
    assert response.top_analog.chembl_id == "CHEMBL25"
    assert response.model_dump()["schema_version"] == "1.0"


def test_ra_decision_response_rejects_invalid_score() -> None:
    with pytest.raises(ValidationError):
        build_ra_decision_response(
            company_id="example_pharma",
            input_compound={"chembl_id": "CHEMBL123"},
            decision=RADecision(
                decision="allow",
                reason="Invalid score should fail.",
                model_score=1.2,
            ),
            thresholds=RAThresholdSnapshot(
                candidate_match=0.65,
                high_confidence_match=0.85,
                manual_review_below=0.55,
            ),
        )


def test_ra_decision_response_rejects_non_triggered_alert_summary() -> None:
    with pytest.raises(ValidationError):
        build_ra_decision_response(
            company_id="example_pharma",
            input_compound={"chembl_id": "CHEMBL123"},
            decision=RADecision(
                decision="review",
                reason="Alert summary should fail.",
                model_score=0.6,
            ),
            thresholds=RAThresholdSnapshot(
                candidate_match=0.65,
                high_confidence_match=0.85,
                manual_review_below=0.55,
            ),
            alert_summaries=[
                {
                    "alert_name": "alerts_epoxide",
                    "triggered": False,
                }
            ],
        )


def test_ra_decision_response_forbids_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        RADecisionResponse.model_validate(
            {
                "company_id": "example_pharma",
                "input_compound": {"chembl_id": "CHEMBL123"},
                "decision": "allow",
                "reason": "No alerts.",
                "score": {
                    "model_score": 0.9,
                    "confidence_band": "high",
                },
                "thresholds": {
                    "candidate_match": 0.65,
                    "high_confidence_match": 0.85,
                    "manual_review_below": 0.55,
                },
                "binary_output": 1,
            }
        )
