from pathlib import Path

from scripts.build_dataset_index import build_index


def test_build_index_returns_expected_rows() -> None:
    dataset_root = Path(
        "/Users/ismailcherkaouiaadil/Downloads/dataset_Similarity_Prediction/original_training_set"
    )

    rows = build_index(dataset_root)

    assert len(rows) == 100
    assert rows[0]["pair_id"] == "001"
    assert rows[0]["has_complete_pdb_pair"] is True
    assert rows[0]["has_complete_svg_pair"] is True
    assert rows[0]["atom_count_a"] == 40
    assert rows[0]["atom_count_b"] == 47
