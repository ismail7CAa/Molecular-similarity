from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


Probability = Annotated[float, Field(ge=0.0, le=1.0)]
Severity = Literal["low", "medium", "high", "critical"]
RuleAction = Literal["allow", "monitor", "review", "block"]
Jurisdiction = Literal["EMA", "FDA", "ICH", "MHRA", "PMDA", "Health Canada"]


class SimilarityThresholds(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidate_match: Probability = Field(
        default=0.65,
        description="Minimum model probability to treat a molecule as similar enough for RA context.",
    )
    high_confidence_match: Probability = Field(
        default=0.85,
        description="Probability above which the match is considered high confidence.",
    )
    manual_review_below: Probability = Field(
        default=0.55,
        description="Below this probability, the engine avoids confident RA recommendations.",
    )

    @field_validator("high_confidence_match")
    @classmethod
    def high_confidence_not_below_candidate(cls, value: float, info) -> float:
        candidate_match = info.data.get("candidate_match")
        if candidate_match is not None and value < candidate_match:
            raise ValueError("high_confidence_match must be >= candidate_match")
        return value


class RegulatoryOutcomeThresholds(BaseModel):
    model_config = ConfigDict(extra="forbid")

    approval_likelihood_review: Probability = Field(
        default=0.50,
        description="Review threshold for model-derived approval or suitability outputs.",
    )
    safety_risk_review: Probability = Field(
        default=0.35,
        description="Safety risk probability that triggers RA review.",
    )
    safety_risk_block: Probability = Field(
        default=0.70,
        description="Safety risk probability that blocks automatic progression.",
    )

    @field_validator("safety_risk_block")
    @classmethod
    def block_not_below_review(cls, value: float, info) -> float:
        review = info.data.get("safety_risk_review")
        if review is not None and value < review:
            raise ValueError("safety_risk_block must be >= safety_risk_review")
        return value


class PhasePolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    minimum_preferred_max_phase: Annotated[float, Field(ge=0.0, le=4.0)] = Field(
        default=2.0,
        description="Preferred minimum ChEMBL max_phase for comparable compounds.",
    )
    require_approved_reference: bool = Field(
        default=False,
        description="Require at least one approved or marketed reference compound.",
    )
    approved_reference_min_phase: Annotated[float, Field(ge=0.0, le=4.0)] = Field(
        default=4.0,
        description="Phase value treated as approved or marketed.",
    )


class AlertPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = True
    default_action: RuleAction = "review"
    severity: Severity = "high"
    rationale: str = Field(
        default="Structural alert requires regulatory review.",
        min_length=1,
    )


class ComplianceRule(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rule_id: str = Field(
        min_length=1,
        pattern=r"^[a-z0-9][a-z0-9_-]*$",
        description="Stable lowercase rule identifier.",
    )
    description: str = Field(min_length=1)
    enabled: bool = True
    action: RuleAction = "review"
    severity: Severity = "medium"
    applies_to_jurisdictions: list[Jurisdiction] = Field(default_factory=list)


class CompanyComplianceConfig(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "title": "Company Compliance Rules Configuration",
            "description": (
                "Human-readable company personalization layer for regulatory "
                "decision intelligence. This config changes context, thresholds, "
                "and rule actions without retraining the model."
            ),
        },
    )

    schema_version: Literal["1.0"] = "1.0"
    company_id: str = Field(
        min_length=1,
        pattern=r"^[a-z0-9][a-z0-9_-]*$",
        description="Stable lowercase company identifier used in config filenames.",
    )
    company_name: str = Field(min_length=1)
    effective_date: date
    owner: str = Field(
        min_length=1,
        description="Responsible RA owner or team for this configuration.",
    )
    jurisdictions: list[Jurisdiction] = Field(
        min_length=1,
        description="Regulatory jurisdictions this config applies to.",
    )
    therapeutic_areas: list[str] = Field(
        default_factory=list,
        description="Company-prioritized therapeutic areas for output context.",
    )
    similarity_thresholds: SimilarityThresholds = Field(
        default_factory=SimilarityThresholds
    )
    outcome_thresholds: RegulatoryOutcomeThresholds = Field(
        default_factory=RegulatoryOutcomeThresholds
    )
    phase_policy: PhasePolicy = Field(default_factory=PhasePolicy)
    structural_alerts: dict[str, AlertPolicy] = Field(
        default_factory=dict,
        description=(
            "Per-alert policy overrides keyed by alert column, for example "
            "alerts_nitrosamine or alerts_pains."
        ),
    )
    rules: list[ComplianceRule] = Field(default_factory=list)
    notes: str = ""

    @field_validator("jurisdictions")
    @classmethod
    def jurisdictions_must_be_unique(cls, value: list[Jurisdiction]) -> list[Jurisdiction]:
        if len(value) != len(set(value)):
            raise ValueError("jurisdictions must be unique")
        return value

    @field_validator("therapeutic_areas")
    @classmethod
    def therapeutic_areas_must_be_unique(cls, value: list[str]) -> list[str]:
        normalized_values = [area.strip() for area in value if area.strip()]
        if len(normalized_values) != len(set(normalized_values)):
            raise ValueError("therapeutic_areas must be unique")
        return normalized_values


def load_company_config(path: Path) -> CompanyComplianceConfig:
    return CompanyComplianceConfig.model_validate_json(path.read_text())


def company_config_json_schema() -> dict[str, object]:
    return CompanyComplianceConfig.model_json_schema()


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Validate company compliance config or print JSON Schema"
    )
    parser.add_argument("config", nargs="?", type=Path, help="Company config JSON file")
    parser.add_argument(
        "--print-schema",
        action="store_true",
        help="Print the company config JSON Schema",
    )
    args = parser.parse_args()

    if args.print_schema:
        print(json.dumps(company_config_json_schema(), indent=2, sort_keys=True))
        return 0

    if args.config is None:
        parser.error("config is required unless --print-schema is used")

    config = load_company_config(args.config)
    print(f"Validated company config: {config.company_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
