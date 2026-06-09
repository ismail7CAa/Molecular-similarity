from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from molecular_similarity.audit_middleware import AuditLogMiddleware
from molecular_similarity.company_onboarding import create_onboarding_router
from molecular_similarity.compliance_config import CompanyComplianceConfig, load_company_config
from molecular_similarity.precedent_matcher import find_top_approved_analog
from molecular_similarity.ra_decision_router import RADecisionRouter
from molecular_similarity.ra_response_schema import (
    RADecisionResponse,
    RAThresholdSnapshot,
    build_ra_decision_response,
)
from molecular_similarity.tenant_namespace import safe_company_id


class PredictRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company_id: str = Field(min_length=1)
    input_compound: dict[str, object]
    model_score: float = Field(ge=0.0, le=1.0)
    alert_flags: dict[str, bool | int | float | str | None] = Field(default_factory=dict)
    top_candidates: list[str | dict[str, Any]] = Field(default_factory=list)
    top_analog: dict[str, object] | None = None
    therapeutic_focus: str | list[str] | None = None


def _path_from_env(name: str, default: str) -> Path:
    return Path(os.environ.get(name, default))


def _config_candidates(config_root: Path, company_id: str) -> list[Path]:
    normalized_company_id = safe_company_id(company_id)
    return [
        config_root / f"{normalized_company_id}.json",
        config_root / normalized_company_id / "config.json",
        config_root / "example_company_config.json",
    ]


def _load_company_config(config_root: Path, company_id: str) -> CompanyComplianceConfig:
    for config_path in _config_candidates(config_root, company_id):
        if config_path.exists():
            config = load_company_config(config_path)
            if config.company_id != safe_company_id(company_id):
                continue
            return config
    raise HTTPException(
        status_code=404,
        detail=f"No company config found for company_id={safe_company_id(company_id)}",
    )


def _alert_summaries(
    config: CompanyComplianceConfig,
    triggered_alerts: list[str],
) -> list[dict[str, object]]:
    summaries: list[dict[str, object]] = []
    for alert_name in triggered_alerts:
        policy = config.structural_alerts.get(alert_name)
        if policy is None:
            continue
        summaries.append(
            {
                "alert_name": alert_name,
                "triggered": True,
                "action": policy.default_action,
                "severity": policy.severity,
                "rationale": policy.rationale,
            }
        )
    return summaries


def _history_count(history_root: Path, company_id: str) -> int:
    history_path = history_root / safe_company_id(company_id) / "ra_decisions.parquet"
    if not history_path.exists():
        return 0
    try:
        import pyarrow.parquet as pq
    except ImportError:
        return 0
    return int(pq.read_table(history_path).num_rows)


def create_app() -> FastAPI:
    config_root = _path_from_env("COMPANY_CONFIG_ROOT", "configs")
    index_root = _path_from_env("COMPANY_INDEX_ROOT", "indexes")
    history_root = _path_from_env("COMPANY_HISTORY_ROOT", "history")
    audit_root = _path_from_env("COMPANY_AUDIT_ROOT", "audit")
    enriched_molecules_path = _path_from_env(
        "ENRICHED_MOLECULES_PATH",
        "data/enriched_molecules.parquet",
    )

    app = FastAPI(
        title="Regulatory Decision Intelligence API",
        version="0.1.0",
        description="Production entrypoint for RA-readable molecular similarity decisions.",
    )
    app.add_middleware(
        AuditLogMiddleware,
        audit_root=audit_root,
        audited_paths=("/predict",),
    )
    app.include_router(
        create_onboarding_router(index_root=index_root, history_root=history_root)
    )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/ready")
    def ready() -> dict[str, object]:
        return {
            "status": "ready",
            "config_root": str(config_root),
            "index_root": str(index_root),
            "history_root": str(history_root),
            "audit_root": str(audit_root),
        }

    @app.post("/predict", response_model=RADecisionResponse)
    def predict(request: PredictRequest) -> RADecisionResponse:
        config = _load_company_config(config_root, request.company_id)
        decision = RADecisionRouter(config).route(
            model_score=request.model_score,
            alert_flags=request.alert_flags,
        )
        thresholds = RAThresholdSnapshot(
            candidate_match=config.similarity_thresholds.candidate_match,
            high_confidence_match=config.similarity_thresholds.high_confidence_match,
            manual_review_below=config.similarity_thresholds.manual_review_below,
        )
        top_analog = request.top_analog
        if top_analog is None and request.top_candidates and enriched_molecules_path.exists():
            top_analog = find_top_approved_analog(
                top_candidates=request.top_candidates,
                therapeutic_focus=request.therapeutic_focus or config.therapeutic_areas,
                enriched_molecules_path=enriched_molecules_path,
                approved_min_phase=config.phase_policy.approved_reference_min_phase,
            )

        history_count = _history_count(history_root, config.company_id)
        response = build_ra_decision_response(
            company_id=config.company_id,
            input_compound=request.input_compound,
            decision=decision,
            thresholds=thresholds,
            alert_summaries=_alert_summaries(
                config=config,
                triggered_alerts=decision.triggered_alerts,
            ),
            top_analog=top_analog,
            audit_trail=[
                {"step": "config", "message": f"Loaded config for {config.company_id}."},
                {"step": "router", "message": decision.reason},
            ],
            ra_justification={
                "summary": decision.reason,
                "score_rationale": (
                    f"Model score {request.model_score:.4f} was evaluated against "
                    "company similarity thresholds."
                ),
                "alert_rationale": (
                    "Triggered configured alerts: " + ", ".join(decision.triggered_alerts)
                    if decision.triggered_alerts
                    else "No configured alerts were triggered."
                ),
                "precedent_rationale": (
                    f"Approved analog {top_analog['chembl_id']} was attached."
                    if top_analog
                    else "No approved analog precedent was attached."
                ),
                "history_rationale": (
                    f"{history_count} company RA history rows are available."
                    if history_count
                    else "No company RA history context was available."
                ),
            },
        )
        return response

    return app


app = create_app()


def main() -> int:
    import uvicorn

    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run("molecular_similarity.api:app", host=host, port=port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
