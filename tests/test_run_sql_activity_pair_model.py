import csv

from molecular_similarity.sql_activity_model import build_report, main, render_markdown


def test_build_report_trains_on_sql_activity_export(tmp_path) -> None:
    export_path = tmp_path / "chembl_modeling.csv"
    fieldnames = [
        "pair_id",
        "split",
        "molecule_a_id",
        "molecule_b_id",
        "molecule_a_chembl_id",
        "molecule_b_chembl_id",
        "compound_name_a",
        "compound_name_b",
        "target_chembl_id",
        "target_name",
        "standard_type",
        "has_conformer_pair",
        "has_image_pair",
        "similarity_score",
        "is_similar",
        "activity_value_a",
        "activity_value_b",
        "activity_unit",
        "activity_delta",
        "activity_value_mean",
        "smiles_a",
        "smiles_b",
        "smiles_length_a",
        "smiles_length_b",
        "smiles_length_abs_delta",
        "molecular_weight_a",
        "molecular_weight_b",
        "molecular_weight_abs_delta",
        "heavy_atom_count_a",
        "heavy_atom_count_b",
        "heavy_atom_count_abs_delta",
    ]
    rows = [
        ["p1", "train", 1, 2, "CHEMBL1", "CHEMBL2", "A", "B", "CHEMBLT1", "Target", "Ki", 0, 0, 0.9, 1, 7.0, 6.9, "pchembl", 0.1, 6.95, "CCN", "CCNC", 3, 4, 1, 0, 0, 0, 0, 0, 0],
        ["p2", "train", 3, 4, "CHEMBL3", "CHEMBL4", "C", "D", "CHEMBLT1", "Target", "Ki", 0, 0, 0.2, 0, 5.0, 2.0, "pchembl", 3.0, 3.5, "CCCCCCCC", "CCCCCCCCCC", 8, 10, 2, 0, 0, 0, 0, 0, 0],
        ["p3", "train", 5, 6, "CHEMBL5", "CHEMBL6", "E", "F", "CHEMBLT2", "Target2", "IC50", 0, 0, 0.85, 1, 6.5, 6.4, "pchembl", 0.1, 6.45, "c1ccncc1", "c1ccncc1F", 8, 9, 1, 0, 0, 0, 0, 0, 0],
        ["p4", "train", 7, 8, "CHEMBL7", "CHEMBL8", "G", "H", "CHEMBLT2", "Target2", "IC50", 0, 0, 0.25, 0, 4.0, 1.5, "pchembl", 2.5, 2.75, "CCCCN", "CCCCCCCCN", 5, 9, 4, 0, 0, 0, 0, 0, 0],
        ["p5", "val", 9, 10, "CHEMBL9", "CHEMBL10", "I", "J", "CHEMBLT1", "Target", "Ki", 0, 0, 0.88, 1, 7.2, 7.1, "pchembl", 0.1, 7.15, "CCNO", "CCNOC", 4, 5, 1, 0, 0, 0, 0, 0, 0],
        ["p6", "val", 11, 12, "CHEMBL11", "CHEMBL12", "K", "L", "CHEMBLT1", "Target", "Ki", 0, 0, 0.22, 0, 4.5, 1.5, "pchembl", 3.0, 3.0, "CCCCCC", "CCCCCCCCCC", 6, 10, 4, 0, 0, 0, 0, 0, 0],
        ["p7", "test", 13, 14, "CHEMBL13", "CHEMBL14", "M", "N", "CHEMBLT2", "Target2", "IC50", 0, 0, 0.83, 1, 6.9, 6.8, "pchembl", 0.1, 6.85, "c1ccccc1N", "c1ccccc1NF", 9, 10, 1, 0, 0, 0, 0, 0, 0],
        ["p8", "test", 15, 16, "CHEMBL15", "CHEMBL16", "O", "P", "CHEMBLT2", "Target2", "IC50", 0, 0, 0.18, 0, 3.5, 1.0, "pchembl", 2.5, 2.25, "CCCCCCC", "CCCCCCCCCCC", 7, 11, 4, 0, 0, 0, 0, 0, 0],
    ]
    with export_path.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(fieldnames)
        writer.writerows(rows)

    report = build_report(export_path)

    assert report["dataset"]["split_counts"] == {"train": 4, "val": 2, "test": 2}
    assert report["configuration"]["selected_feature_set"] in {
        "structure_proxy",
        "structure_enriched",
        "structure_plus_context",
    }
    assert set(report["model"]["metrics"]) == {"development", "test"}
    assert len(report["test_examples"]) == 2


def test_render_markdown_includes_sql_model_summary() -> None:
    report = {
        "configuration": {
            "export_path": "data/chembl_modeling.csv",
            "selected_feature_set": "structure_proxy",
            "selected_probability_threshold": 0.5,
            "selected_l2_penalty": 0.1,
        },
        "dataset": {
            "row_count": 8,
            "split_counts": {"train": 4, "val": 2, "test": 2},
            "label_balance": {"similar": 4, "dissimilar": 4},
        },
        "model_selection": {
            "selected_configuration": {
                "validation_metrics": {"accuracy": 1.0, "f1": 1.0, "log_loss": 0.1}
            }
        },
        "model": {
            "metrics": {
                "development": {
                    "log_loss": 0.1,
                    "brier_score": 0.01,
                    "accuracy": 1.0,
                    "precision": 1.0,
                    "recall": 1.0,
                    "f1": 1.0,
                },
                "test": {
                    "log_loss": 0.2,
                    "brier_score": 0.02,
                    "accuracy": 1.0,
                    "precision": 1.0,
                    "recall": 1.0,
                    "f1": 1.0,
                },
            }
        },
        "test_examples": [
            {
                "pair_id": "p7",
                "target_name": "Target2",
                "standard_type": "IC50",
                "similarity_score": 0.83,
                "activity_delta": 0.1,
                "actual_label": 1,
                "predicted_probability": 0.95,
                "predicted_label": 1,
            }
        ],
    }

    markdown = render_markdown(report)

    assert "# SQL Activity Pair Model" in markdown
    assert "## Classification Metrics" in markdown
    assert "| p7 | Target2 | IC50 | 0.83 | 0.1 | 1 | 0.95 | 1 |" in markdown


def test_main_writes_reports_via_cli(tmp_path, monkeypatch) -> None:
    export_path = tmp_path / "chembl_modeling.csv"
    with export_path.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "pair_id",
                "split",
                "molecule_a_id",
                "molecule_b_id",
                "molecule_a_chembl_id",
                "molecule_b_chembl_id",
                "compound_name_a",
                "compound_name_b",
                "target_chembl_id",
                "target_name",
                "standard_type",
                "has_conformer_pair",
                "has_image_pair",
                "similarity_score",
                "is_similar",
                "activity_value_a",
                "activity_value_b",
                "activity_unit",
                "activity_delta",
                "activity_value_mean",
                "smiles_a",
                "smiles_b",
                "smiles_length_a",
                "smiles_length_b",
                "smiles_length_abs_delta",
                "molecular_weight_a",
                "molecular_weight_b",
                "molecular_weight_abs_delta",
                "heavy_atom_count_a",
                "heavy_atom_count_b",
                "heavy_atom_count_abs_delta",
            ]
        )
        writer.writerows(
            [
                ["p1", "train", 1, 2, "CHEMBL1", "CHEMBL2", "A", "B", "CHEMBLT1", "Target", "Ki", 0, 0, 0.9, 1, 7.0, 6.9, "pchembl", 0.1, 6.95, "CCN", "CCNC", 3, 4, 1, 0, 0, 0, 0, 0, 0],
                ["p2", "train", 3, 4, "CHEMBL3", "CHEMBL4", "C", "D", "CHEMBLT1", "Target", "Ki", 0, 0, 0.2, 0, 5.0, 2.0, "pchembl", 3.0, 3.5, "CCCCCCCC", "CCCCCCCCCC", 8, 10, 2, 0, 0, 0, 0, 0, 0],
                ["p3", "val", 5, 6, "CHEMBL5", "CHEMBL6", "E", "F", "CHEMBLT2", "Target2", "IC50", 0, 0, 0.85, 1, 6.5, 6.4, "pchembl", 0.1, 6.45, "c1ccncc1", "c1ccncc1F", 8, 9, 1, 0, 0, 0, 0, 0, 0],
                ["p4", "val", 7, 8, "CHEMBL7", "CHEMBL8", "G", "H", "CHEMBLT2", "Target2", "IC50", 0, 0, 0.25, 0, 4.0, 1.5, "pchembl", 2.5, 2.75, "CCCCN", "CCCCCCCCN", 5, 9, 4, 0, 0, 0, 0, 0, 0],
                ["p5", "test", 9, 10, "CHEMBL9", "CHEMBL10", "I", "J", "CHEMBLT1", "Target", "Ki", 0, 0, 0.88, 1, 7.2, 7.1, "pchembl", 0.1, 7.15, "CCNO", "CCNOC", 4, 5, 1, 0, 0, 0, 0, 0, 0],
                ["p6", "test", 11, 12, "CHEMBL11", "CHEMBL12", "K", "L", "CHEMBLT1", "Target", "Ki", 0, 0, 0.22, 0, 4.5, 1.5, "pchembl", 3.0, 3.0, "CCCCCC", "CCCCCCCCCC", 6, 10, 4, 0, 0, 0, 0, 0, 0],
            ]
        )

    reports_dir = tmp_path / "reports"
    exit_code = main([str(export_path), "--reports-dir", str(reports_dir)])

    assert exit_code == 0
    assert (reports_dir / "sql_activity_pair_model.json").exists()
    assert (reports_dir / "sql_activity_pair_model.md").exists()
