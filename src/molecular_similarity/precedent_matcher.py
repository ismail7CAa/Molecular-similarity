from __future__ import annotations

from pathlib import Path
from typing import Any


DEFAULT_ENRICHED_MOLECULES_PATH = Path("data/enriched_molecules.parquet")


def _read_enriched_rows(enriched_molecules_path: Path) -> list[dict[str, object]]:
    try:
        import pyarrow.parquet as pq
    except ImportError as error:
        raise RuntimeError(
            "Reading enriched_molecules.parquet requires pyarrow. "
            "Install project dependencies with: pip install -e .[dev]"
        ) from error

    table = pq.read_table(enriched_molecules_path)
    return table.to_pylist()


def _candidate_chembl_id(candidate: str | dict[str, Any]) -> str:
    if isinstance(candidate, str):
        return candidate
    return str(candidate.get("chembl_id") or candidate.get("molecule_chembl_id") or "")


def _candidate_score(candidate: str | dict[str, Any]) -> float:
    if isinstance(candidate, str):
        return 0.0
    score = candidate.get("score", candidate.get("model_score", candidate.get("similarity_score", 0.0)))
    return float(score or 0.0)


def _matches_therapeutic_focus(
    therapeutic_area: object,
    therapeutic_focus: str | list[str] | None,
) -> bool:
    if not therapeutic_focus:
        return True

    if isinstance(therapeutic_focus, str):
        focus_values = [therapeutic_focus]
    else:
        focus_values = therapeutic_focus

    normalized_area = str(therapeutic_area or "").strip().lower()
    normalized_focus = [
        str(focus).strip().lower()
        for focus in focus_values
        if str(focus).strip()
    ]
    return any(focus in normalized_area for focus in normalized_focus)


def find_top_approved_analog(
    top_candidates: list[str | dict[str, Any]],
    therapeutic_focus: str | list[str] | None = None,
    enriched_molecules_path: Path = DEFAULT_ENRICHED_MOLECULES_PATH,
    approved_min_phase: float = 4.0,
) -> dict[str, object] | None:
    """Return the most relevant approved analog from top-N model candidates."""
    if not top_candidates:
        return None

    candidate_order: dict[str, int] = {}
    candidate_scores: dict[str, float] = {}
    for index, candidate in enumerate(top_candidates):
        chembl_id = _candidate_chembl_id(candidate)
        if not chembl_id:
            continue
        candidate_order.setdefault(chembl_id, index)
        candidate_scores[chembl_id] = _candidate_score(candidate)

    if not candidate_order:
        return None

    enriched_by_chembl_id = {
        str(row.get("chembl_id")): row
        for row in _read_enriched_rows(enriched_molecules_path)
    }

    eligible_rows: list[dict[str, object]] = []
    for chembl_id in candidate_order:
        row = enriched_by_chembl_id.get(chembl_id)
        if row is None:
            continue
        if float(row.get("max_phase") or 0.0) < approved_min_phase:
            continue
        if not _matches_therapeutic_focus(row.get("therapeutic_area"), therapeutic_focus):
            continue
        eligible_rows.append(row)

    if not eligible_rows:
        return None

    best_row = max(
        eligible_rows,
        key=lambda row: (
            -candidate_order[str(row.get("chembl_id"))],
            float(row.get("max_phase") or 0.0),
            int(row.get("first_approval") or 0),
            candidate_scores.get(str(row.get("chembl_id")), 0.0),
        ),
    )

    chembl_id = str(best_row.get("chembl_id") or "")
    return {
        "chembl_id": chembl_id,
        "name": best_row.get("compound_name") or "",
        "max_phase": float(best_row.get("max_phase") or 0.0),
        "approval_year": best_row.get("first_approval") or None,
    }
