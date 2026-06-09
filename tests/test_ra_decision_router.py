from pathlib import Path

import pytest

from molecular_similarity.compliance_config import load_company_config
from molecular_similarity.ra_decision_router import RADecisionRouter


def _router() -> RADecisionRouter:
    return RADecisionRouter(load_company_config(Path("configs/example_company_config.json")))


def test_high_model_score_allows_when_no_alerts_trigger() -> None:
    decision = _router().route(model_score=0.91, alert_flags={})

    assert decision.as_tuple() == (
        "allow",
        "Model score meets high_confidence_match and no enabled alerts were triggered.",
    )
    assert decision.triggered_alerts == []


def test_alert_escalation_overrides_high_model_score() -> None:
    decision = _router().route(
        model_score=0.98,
        alert_flags={
            "alerts_nitrosamine": 1,
            "alerts_epoxide": 0,
        },
    )

    assert decision.decision == "block"
    assert "Alert escalation override" in decision.reason
    assert "alerts_nitrosamine" in decision.reason
    assert decision.triggered_alerts == ["alerts_nitrosamine"]


def test_router_uses_strongest_triggered_alert_policy() -> None:
    decision = _router().route(
        model_score=0.98,
        alert_flags={
            "alerts_pains": True,
            "alerts_epoxide": True,
            "alerts_nitrosamine": True,
        },
    )

    assert decision.decision == "block"
    assert "alerts_nitrosamine" in decision.reason
    assert sorted(decision.triggered_alerts) == [
        "alerts_epoxide",
        "alerts_nitrosamine",
        "alerts_pains",
    ]


def test_unconfigured_alert_does_not_override_score() -> None:
    decision = _router().route(
        model_score=0.9,
        alert_flags={"alerts_unconfigured": True},
    )

    assert decision.decision == "allow"
    assert decision.triggered_alerts == []


def test_candidate_score_monitors_without_alerts() -> None:
    decision = _router().route_tuple(
        model_score=0.7,
        alert_flags={"alerts_nitrosamine": 0},
    )

    assert decision == (
        "monitor",
        "Model score meets candidate_match but not high_confidence_match.",
    )


def test_low_score_requires_review_without_alerts() -> None:
    decision = _router().route(model_score=0.4, alert_flags={})

    assert decision.decision == "review"
    assert "manual_review_below" in decision.reason


def test_router_rejects_invalid_model_score() -> None:
    with pytest.raises(ValueError, match="model_score"):
        _router().route(model_score=1.5, alert_flags={})
