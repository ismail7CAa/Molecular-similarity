from pathlib import Path

import pytest
from pydantic import ValidationError

from molecular_similarity.compliance_config import (
    CompanyComplianceConfig,
    company_config_json_schema,
    load_company_config,
)


def test_example_company_config_validates() -> None:
    config = load_company_config(Path("configs/example_company_config.json"))

    assert config.company_id == "example_pharma"
    assert config.jurisdictions == ["FDA", "EMA", "ICH"]
    assert config.structural_alerts["alerts_nitrosamine"].default_action == "block"


def test_company_config_rejects_unknown_fields() -> None:
    payload = {
        "schema_version": "1.0",
        "company_id": "example_pharma",
        "company_name": "Example Pharma",
        "effective_date": "2026-06-08",
        "owner": "Regulatory Affairs",
        "jurisdictions": ["FDA"],
        "retrain_model": True,
    }

    with pytest.raises(ValidationError):
        CompanyComplianceConfig.model_validate(payload)


def test_company_config_validates_threshold_ordering() -> None:
    payload = {
        "schema_version": "1.0",
        "company_id": "example_pharma",
        "company_name": "Example Pharma",
        "effective_date": "2026-06-08",
        "owner": "Regulatory Affairs",
        "jurisdictions": ["FDA"],
        "similarity_thresholds": {
            "candidate_match": 0.8,
            "high_confidence_match": 0.7,
            "manual_review_below": 0.5,
        },
    }

    with pytest.raises(ValidationError, match="high_confidence_match"):
        CompanyComplianceConfig.model_validate(payload)


def test_company_config_json_schema_exposes_required_ra_fields() -> None:
    schema = company_config_json_schema()

    assert schema["properties"]["company_id"]["type"] == "string"
    assert "jurisdictions" in schema["required"]
    assert "similarity_thresholds" in schema["properties"]
    assert "structural_alerts" in schema["properties"]
