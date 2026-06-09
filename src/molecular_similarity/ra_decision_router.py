from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from molecular_similarity.compliance_config import CompanyComplianceConfig, RuleAction, Severity


Decision = Literal["allow", "monitor", "review", "block"]

ACTION_PRECEDENCE: dict[Decision, int] = {
    "allow": 0,
    "monitor": 1,
    "review": 2,
    "block": 3,
}
SEVERITY_PRECEDENCE: dict[Severity, int] = {
    "low": 0,
    "medium": 1,
    "high": 2,
    "critical": 3,
}


@dataclass(frozen=True)
class RADecision:
    decision: Decision
    reason: str
    model_score: float
    triggered_alerts: list[str] = field(default_factory=list)

    def as_tuple(self) -> tuple[Decision, str]:
        return self.decision, self.reason


class RADecisionRouter:
    """Deterministic regulatory decision router on top of model outputs."""

    def __init__(self, company_config: CompanyComplianceConfig):
        self.company_config = company_config

    def route(
        self,
        model_score: float,
        alert_flags: dict[str, bool | int | float | str | None] | None = None,
    ) -> RADecision:
        if not 0.0 <= model_score <= 1.0:
            raise ValueError("model_score must be between 0.0 and 1.0")

        alert_flags = alert_flags or {}
        alert_decision = self._decision_from_alerts(alert_flags)
        if alert_decision is not None:
            return RADecision(
                decision=alert_decision[0],
                reason=alert_decision[1],
                model_score=model_score,
                triggered_alerts=alert_decision[2],
            )

        score_decision, score_reason = self._decision_from_score(model_score)
        return RADecision(
            decision=score_decision,
            reason=score_reason,
            model_score=model_score,
            triggered_alerts=[],
        )

    def route_tuple(
        self,
        model_score: float,
        alert_flags: dict[str, bool | int | float | str | None] | None = None,
    ) -> tuple[Decision, str]:
        """Return the requested compact (decision, reason) tuple."""
        return self.route(model_score=model_score, alert_flags=alert_flags).as_tuple()

    def _decision_from_alerts(
        self,
        alert_flags: dict[str, bool | int | float | str | None],
    ) -> tuple[Decision, str, list[str]] | None:
        triggered: list[tuple[str, RuleAction, Severity, str]] = []

        for alert_name, alert_value in alert_flags.items():
            if not self._is_triggered(alert_value):
                continue

            policy = self.company_config.structural_alerts.get(alert_name)
            if policy is None or not policy.enabled:
                continue

            triggered.append(
                (
                    alert_name,
                    policy.default_action,
                    policy.severity,
                    policy.rationale,
                )
            )

        if not triggered:
            return None

        strongest = max(
            triggered,
            key=lambda item: (
                ACTION_PRECEDENCE[item[1]],
                SEVERITY_PRECEDENCE[item[2]],
                item[0],
            ),
        )
        alert_name, action, severity, rationale = strongest
        triggered_names = [item[0] for item in triggered]
        reason = (
            f"Alert escalation override: {alert_name} triggered "
            f"{severity} {action}. {rationale}"
        )
        return action, reason, triggered_names

    def _decision_from_score(self, model_score: float) -> tuple[Decision, str]:
        thresholds = self.company_config.similarity_thresholds

        if model_score < thresholds.manual_review_below:
            return (
                "review",
                (
                    "Model score is below manual_review_below; "
                    "RA review required before making a compliance recommendation."
                ),
            )

        if model_score >= thresholds.high_confidence_match:
            return (
                "allow",
                "Model score meets high_confidence_match and no enabled alerts were triggered.",
            )

        if model_score >= thresholds.candidate_match:
            return (
                "monitor",
                "Model score meets candidate_match but not high_confidence_match.",
            )

        return (
            "review",
            "Model score is below candidate_match; RA review required.",
        )

    @staticmethod
    def _is_triggered(value: bool | int | float | str | None) -> bool:
        if value is None:
            return False
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "y"}
        return bool(value)
