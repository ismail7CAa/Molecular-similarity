from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from molecular_similarity.precedent_matcher import find_top_approved_analog


def _write_enriched_lookup(path: Path) -> None:
    rows = [
        {
            "chembl_id": "CHEMBL1",
            "compound_name": "Phase Two Analog",
            "max_phase": 2.0,
            "first_approval": None,
            "therapeutic_area": "Oncology",
        },
        {
            "chembl_id": "CHEMBL2",
            "compound_name": "Approved Cardio Analog",
            "max_phase": 4.0,
            "first_approval": 2012,
            "therapeutic_area": "Cardiology",
        },
        {
            "chembl_id": "CHEMBL3",
            "compound_name": "Approved Oncology Analog",
            "max_phase": 4.0,
            "first_approval": 2004,
            "therapeutic_area": "Oncology; Rare Diseases",
        },
    ]
    pq.write_table(pa.Table.from_pylist(rows), path)


def test_find_top_approved_analog_filters_by_therapeutic_focus(
    tmp_path: Path,
) -> None:
    lookup_path = tmp_path / "enriched_molecules.parquet"
    _write_enriched_lookup(lookup_path)

    top_analog = find_top_approved_analog(
        top_candidates=[
            {"chembl_id": "CHEMBL1", "score": 0.99},
            {"chembl_id": "CHEMBL2", "score": 0.95},
            {"chembl_id": "CHEMBL3", "score": 0.91},
        ],
        therapeutic_focus="Oncology",
        enriched_molecules_path=lookup_path,
    )

    assert top_analog == {
        "chembl_id": "CHEMBL3",
        "name": "Approved Oncology Analog",
        "max_phase": 4.0,
        "approval_year": 2004,
    }


def test_find_top_approved_analog_prefers_earlier_candidate_order(
    tmp_path: Path,
) -> None:
    lookup_path = tmp_path / "enriched_molecules.parquet"
    _write_enriched_lookup(lookup_path)

    top_analog = find_top_approved_analog(
        top_candidates=[
            {"chembl_id": "CHEMBL3", "score": 0.9},
            {"chembl_id": "CHEMBL2", "score": 0.99},
        ],
        enriched_molecules_path=lookup_path,
    )

    assert top_analog["chembl_id"] == "CHEMBL3"


def test_find_top_approved_analog_returns_none_without_eligible_precedent(
    tmp_path: Path,
) -> None:
    lookup_path = tmp_path / "enriched_molecules.parquet"
    _write_enriched_lookup(lookup_path)

    top_analog = find_top_approved_analog(
        top_candidates=["CHEMBL1"],
        therapeutic_focus="Oncology",
        enriched_molecules_path=lookup_path,
    )

    assert top_analog is None
