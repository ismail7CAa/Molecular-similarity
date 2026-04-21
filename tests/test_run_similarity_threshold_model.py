import json

from molecular_similarity.threshold_model import build_report, main, render_markdown


def test_build_report_trains_threshold_classifier(tmp_path) -> None:
    prepared_dataset_path = tmp_path / "prepared_dataset.json"
    labels_path = tmp_path / "labels.csv"

    prepared_dataset_path.write_text(
        json.dumps(
            {
                "rows": [
                    {
                        "pair_id": "001",
                        "split": "train",
                        "atom_count_a": 10,
                        "atom_count_b": 11,
                        "heavy_atom_count_a": 5,
                        "heavy_atom_count_b": 6,
                        "atom_count_delta": 1,
                        "heavy_atom_count_delta": 1,
                        "element_counts_a": '{"C": 4, "H": 5, "N": 1}',
                        "element_counts_b": '{"C": 5, "H": 5, "N": 1}',
                    },
                    {
                        "pair_id": "002",
                        "split": "train",
                        "atom_count_a": 10,
                        "atom_count_b": 22,
                        "heavy_atom_count_a": 5,
                        "heavy_atom_count_b": 11,
                        "atom_count_delta": 12,
                        "heavy_atom_count_delta": 6,
                        "element_counts_a": '{"C": 4, "H": 5, "N": 1}',
                        "element_counts_b": '{"C": 10, "H": 10, "O": 2}',
                    },
                    {
                        "pair_id": "003",
                        "split": "val",
                        "atom_count_a": 12,
                        "atom_count_b": 13,
                        "heavy_atom_count_a": 6,
                        "heavy_atom_count_b": 7,
                        "atom_count_delta": 1,
                        "heavy_atom_count_delta": 1,
                        "element_counts_a": '{"C": 5, "H": 6, "N": 1}',
                        "element_counts_b": '{"C": 6, "H": 6, "N": 1}',
                    },
                    {
                        "pair_id": "004",
                        "split": "test",
                        "atom_count_a": 12,
                        "atom_count_b": 24,
                        "heavy_atom_count_a": 6,
                        "heavy_atom_count_b": 12,
                        "atom_count_delta": 12,
                        "heavy_atom_count_delta": 6,
                        "element_counts_a": '{"C": 5, "H": 6, "N": 1}',
                        "element_counts_b": '{"C": 11, "H": 11, "O": 2}',
                    },
                ]
            }
        )
    )
    labels_path.write_text(
        "\n".join(
            [
                (
                    "id_pair,frac_similar,target_name,pair_type,"
                    "tanimoto_cdk_Extended,TanimotoCombo,pchembl_distance,"
                    "curated_smiles_molecule_a,curated_smiles_molecule_b"
                ),
                "1,0.9,CYP2D6,sim2D,0.95,1.9,0.1,CCN,CCCN",
                "2,0.1,CYP2D6,dis2D,0.15,0.2,1.3,CCN,CCCCCCCC",
                "3,0.8,HERG,sim3D,0.9,1.7,0.2,CCO,CCCO",
                "4,0.2,HERG,dis3D,0.2,0.3,1.1,CCO,CCCCCCCCO",
            ]
        )
    )

    report = build_report(prepared_dataset_path, labels_path, threshold=0.5)

    assert report["configuration"]["label_threshold"] == 0.5
    assert report["dataset"]["split_counts"] == {"train": 2, "val": 1, "test": 1}
    assert report["model"]["name"] == "cross_validated_logistic_threshold_classifier"
    assert set(report["model"]["metrics"]) == {"development", "test"}
    assert report["model_selection"]["selected_configuration"]["feature_set_name"] in {
        "core_similarity",
        "compact_similarity",
    }
    assert len(report["visualization_rows"]) == 4
    assert len(report["visualization_features"]) == 4
    assert report["test_examples"][0]["pair_id"] == "004"
    assert report["test_examples"][0]["actual_label"] == 0
    assert 0.0 <= report["test_examples"][0]["predicted_probability"] <= 1.0


def test_render_markdown_includes_threshold_predictions() -> None:
    report = {
        "configuration": {
            "label_threshold": 0.5,
            "selected_probability_threshold": 0.45,
            "selected_feature_set": "compact_similarity",
            "selected_l2_penalty": 0.1,
            "numeric_feature_count": 3,
            "categorical_feature_count": 1,
        },
        "dataset": {
            "row_count": 4,
            "split_counts": {"train": 2, "val": 1, "test": 1},
        },
        "model_selection": {
            "fold_count": 5,
            "selected_configuration": {
                "cv_metrics": {
                    "mean_f1": 0.9,
                    "mean_accuracy": 0.8,
                    "mean_log_loss": 0.3,
                }
            },
        },
        "model": {
            "metrics": {
                "development": {
                    "log_loss": 0.1,
                    "brier_score": 0.02,
                    "accuracy": 1.0,
                    "precision": 1.0,
                    "recall": 1.0,
                    "f1": 1.0,
                },
                "test": {
                    "log_loss": 0.3,
                    "brier_score": 0.08,
                    "accuracy": 1.0,
                    "precision": 1.0,
                    "recall": 1.0,
                    "f1": 1.0,
                },
            }
        },
        "plots": {
            "probability_distribution": "similarity_threshold_model_probability.png",
            "umap_projection": "similarity_threshold_model_umap.png",
        },
        "test_examples": [
            {
                "pair_id": "004",
                "target_name": "HERG",
                "pair_type": "dis3D",
                "actual_frac_similar": 0.2,
                "actual_label": 0,
                "predicted_probability": 0.1,
                "predicted_label": 0,
            }
        ],
    }

    markdown = render_markdown(report)

    assert "# Threshold-Based Similarity Model" in markdown
    assert "## Model Selection" in markdown
    assert "## Plots" in markdown
    assert "## Classification Metrics" in markdown
    assert "similarity_threshold_model_umap.png" in markdown
    assert "| 004 | HERG | dis3D | 0.2 | 0 | 0.1 | 0 |" in markdown


def test_main_writes_reports_via_cli(tmp_path) -> None:
    prepared_dataset_path = tmp_path / "prepared_dataset.json"
    labels_path = tmp_path / "labels.csv"
    reports_dir = tmp_path / "reports"

    prepared_dataset_path.write_text(
        json.dumps(
            {
                "rows": [
                    {
                        "pair_id": "001",
                        "split": "train",
                        "atom_count_a": 10,
                        "atom_count_b": 11,
                        "heavy_atom_count_a": 5,
                        "heavy_atom_count_b": 6,
                        "atom_count_delta": 1,
                        "heavy_atom_count_delta": 1,
                        "element_counts_a": '{"C": 4, "H": 5, "N": 1}',
                        "element_counts_b": '{"C": 5, "H": 5, "N": 1}',
                    },
                    {
                        "pair_id": "002",
                        "split": "train",
                        "atom_count_a": 10,
                        "atom_count_b": 22,
                        "heavy_atom_count_a": 5,
                        "heavy_atom_count_b": 11,
                        "atom_count_delta": 12,
                        "heavy_atom_count_delta": 6,
                        "element_counts_a": '{"C": 4, "H": 5, "N": 1}',
                        "element_counts_b": '{"C": 10, "H": 10, "O": 2}',
                    },
                    {
                        "pair_id": "003",
                        "split": "train",
                        "atom_count_a": 12,
                        "atom_count_b": 13,
                        "heavy_atom_count_a": 6,
                        "heavy_atom_count_b": 7,
                        "atom_count_delta": 1,
                        "heavy_atom_count_delta": 1,
                        "element_counts_a": '{"C": 5, "H": 6, "N": 1}',
                        "element_counts_b": '{"C": 6, "H": 6, "N": 1}',
                    },
                    {
                        "pair_id": "004",
                        "split": "train",
                        "atom_count_a": 12,
                        "atom_count_b": 24,
                        "heavy_atom_count_a": 6,
                        "heavy_atom_count_b": 12,
                        "atom_count_delta": 12,
                        "heavy_atom_count_delta": 6,
                        "element_counts_a": '{"C": 5, "H": 6, "N": 1}',
                        "element_counts_b": '{"C": 11, "H": 11, "O": 2}',
                    },
                    {
                        "pair_id": "005",
                        "split": "val",
                        "atom_count_a": 11,
                        "atom_count_b": 12,
                        "heavy_atom_count_a": 5,
                        "heavy_atom_count_b": 6,
                        "atom_count_delta": 1,
                        "heavy_atom_count_delta": 1,
                        "element_counts_a": '{"C": 4, "H": 6, "N": 1}',
                        "element_counts_b": '{"C": 5, "H": 6, "N": 1}',
                    },
                    {
                        "pair_id": "006",
                        "split": "val",
                        "atom_count_a": 11,
                        "atom_count_b": 23,
                        "heavy_atom_count_a": 5,
                        "heavy_atom_count_b": 12,
                        "atom_count_delta": 12,
                        "heavy_atom_count_delta": 7,
                        "element_counts_a": '{"C": 4, "H": 6, "N": 1}',
                        "element_counts_b": '{"C": 11, "H": 10, "O": 2}',
                    },
                    {
                        "pair_id": "007",
                        "split": "test",
                        "atom_count_a": 13,
                        "atom_count_b": 14,
                        "heavy_atom_count_a": 6,
                        "heavy_atom_count_b": 7,
                        "atom_count_delta": 1,
                        "heavy_atom_count_delta": 1,
                        "element_counts_a": '{"C": 5, "H": 7, "N": 1}',
                        "element_counts_b": '{"C": 6, "H": 7, "N": 1}',
                    },
                    {
                        "pair_id": "008",
                        "split": "test",
                        "atom_count_a": 13,
                        "atom_count_b": 25,
                        "heavy_atom_count_a": 6,
                        "heavy_atom_count_b": 12,
                        "atom_count_delta": 12,
                        "heavy_atom_count_delta": 6,
                        "element_counts_a": '{"C": 5, "H": 7, "N": 1}',
                        "element_counts_b": '{"C": 12, "H": 11, "O": 2}',
                    },
                ]
            }
        )
    )
    labels_path.write_text(
        "\n".join(
            [
                (
                    "id_pair,frac_similar,target_name,pair_type,"
                    "tanimoto_cdk_Extended,TanimotoCombo,pchembl_distance,"
                    "curated_smiles_molecule_a,curated_smiles_molecule_b"
                ),
                "1,0.9,CYP2D6,sim2D,0.95,1.9,0.1,CCN,CCCN",
                "2,0.1,CYP2D6,dis2D,0.15,0.2,1.3,CCN,CCCCCCCC",
                "3,0.85,HERG,sim3D,0.92,1.75,0.15,CCO,CCCO",
                "4,0.2,HERG,dis3D,0.2,0.3,1.1,CCO,CCCCCCCCO",
                "5,0.82,5HT2B,sim2D,0.9,1.8,0.2,CNC,CNCC",
                "6,0.18,5HT2B,dis2D,0.18,0.25,1.25,CNC,CCCCCCNC",
                "7,0.88,CYP2D6,sim3D,0.94,1.85,0.12,CCCN,CCCCN",
                "8,0.12,CYP2D6,dis3D,0.16,0.22,1.4,CCCN,CCCCCCCCCN",
            ]
        )
    )

    exit_code = main(
        [
            str(prepared_dataset_path),
            str(labels_path),
            "0.5",
            "--reports-dir",
            str(reports_dir),
        ]
    )

    assert exit_code == 0
    assert (reports_dir / "similarity_threshold_model.json").exists()
    assert (reports_dir / "similarity_threshold_model.md").exists()
