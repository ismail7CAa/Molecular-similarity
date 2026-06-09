from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from molecular_similarity.ra_decision_router import Decision, RADecision


Probability = Annotated[float, Field(ge=0.0, le=1.0)]
ConfidenceBand = Literal["low", "candidate", "high"]


class RAInputCompound(BaseModel):
    model_config = ConfigDict(extra="forbid")

    chembl_id: str = Field(min_length=1)
    name: str = ""
    smiles: str = ""


class RAScoreSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model_score: Probability
    confidence_band: ConfidenceBand
    threshold_source: str = Field(
        default="company_config.similarity_thresholds",
        min_length=1,
    )


class RAAlertSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    alert_name: str = Field(min_length=1)
    triggered: bool
    action: Literal["allow", "monitor", "review", "block"] = "review"
    severity: Literal["low", "medium", "high", "critical"] = "medium"
    rationale: str = ""


class RAPrecedentAnalog(BaseModel):
    model_config = ConfigDict(extra="forbid")

    chembl_id: str = Field(min_length=1)
    name: str = ""
    max_phase: Annotated[float, Field(ge=0.0, le=4.0)]
    approval_year: int | None = Field(default=None, ge=1800, le=2100)


class RAThresholdSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidate_match: Probability
    high_confidence_match: Probability
    manual_review_below: Probability

    @model_validator(mode="after")
    def validate_threshold_order(self) -> RAThresholdSnapshot:
        if self.high_confidence_match < self.candidate_match:
            raise ValueError("high_confidence_match must be >= candidate_match")
        return self


class RAAuditEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    step: str = Field(min_length=1)
    message: str = Field(min_length=1)


class RAJustification(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str = Field(min_length=1)
    score_rationale: str = Field(min_length=1)
    alert_rationale: str = Field(default="No configured alerts were triggered.")
    precedent_rationale: str = Field(default="No approved analog precedent was found.")
    history_rationale: str = Field(default="No company RA history context was attached.")


class RADecisionResponse(BaseModel):
    """Auditable RA-readable response object returned by the compliance API."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.0"] = "1.0"
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    company_id: str = Field(min_length=1)
    input_compound: RAInputCompound
    decision: Decision
    reason: str = Field(min_length=1)
    ra_justification: RAJustification
    score: RAScoreSummary
    triggered_alerts: list[RAAlertSummary] = Field(default_factory=list)
    top_analog: RAPrecedentAnalog | None = None
    thresholds: RAThresholdSnapshot
    audit_trail: list[RAAuditEvent] = Field(default_factory=list)

    @field_validator("triggered_alerts")
    @classmethod
    def alert_summaries_must_be_triggered(
        cls,
        value: list[RAAlertSummary],
    ) -> list[RAAlertSummary]:
        if any(not alert.triggered for alert in value):
            raise ValueError("triggered_alerts must only contain triggered alerts")
        return value


def confidence_band_for_score(
    model_score: float,
    thresholds: RAThresholdSnapshot,
) -> ConfidenceBand:
    if model_score >= thresholds.high_confidence_match:
        return "high"
    if model_score >= thresholds.candidate_match:
        return "candidate"
    return "low"


def build_ra_decision_response(
    *,
    company_id: str,
    input_compound: dict[str, object],
    decision: RADecision,
    thresholds: RAThresholdSnapshot,
    alert_summaries: list[dict[str, object]] | None = None,
    top_analog: dict[str, object] | None = None,
    audit_trail: list[dict[str, object]] | None = None,
    ra_justification: dict[str, object] | None = None,
) -> RADecisionResponse:
    """Build and validate the full RA response object on every call."""
    score_band = confidence_band_for_score(decision.model_score, thresholds)
    default_justification = {
        "summary": decision.reason,
        "score_rationale": (
            f"Model score {decision.model_score:.4f} maps to {score_band} confidence "
            "using company similarity thresholds."
        ),
        "alert_rationale": (
            "Triggered alerts: " + ", ".join(decision.triggered_alerts)
            if decision.triggered_alerts
            else "No configured alerts were triggered."
        ),
        "precedent_rationale": (
            "Approved analog precedent attached: "
            + str(top_analog.get("chembl_id"))
            if top_analog
            else "No approved analog precedent was found."
        ),
        "history_rationale": "No company RA history context was attached.",
    }
    return RADecisionResponse.model_validate(
        {
            "company_id": company_id,
            "input_compound": input_compound,
            "decision": decision.decision,
            "reason": decision.reason,
            "ra_justification": ra_justification or default_justification,
            "score": {
                "model_score": decision.model_score,
                "confidence_band": score_band,
            },
            "triggered_alerts": alert_summaries or [],
            "top_analog": top_analog,
            "thresholds": thresholds.model_dump(),
            "audit_trail": audit_trail or [],
        }
    )
