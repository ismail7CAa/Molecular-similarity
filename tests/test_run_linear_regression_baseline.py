import json

from molecular_similarity.linear_regression_baseline import (
    build_feature_names,
    build_modeling_rows,
    evaluate_probabilities,
    evaluate_regression_with_threshold,
    main,
    predict,
    predict_probabilities,
    train_linear_regression,
    train_logistic_regression,
)


def test_build_modeling_rows_creates_richer_features() -> None:
    prepared_rows = [
        {
            "pair_id": "001",
            "split": "train",
            "atom_count_a": 10,
            "atom_count_b": 12,
            "heavy_atom_count_a": 5,
            "heavy_atom_count_b": 6,
            "atom_count_delta": 2,
            "heavy_atom_count_delta": 1,
            "element_counts_a": '{"C": 4, "H": 5, "N": 1}',
            "element_counts_b": '{"C": 5, "H": 5, "O": 2}',
        }
    ]
    labels = {
        "001": {
            "frac_similar": "0.7",
            "target_name": "CYP2D6",
            "pair_type": "sim2D,sim3D",
            "tanimoto_cdk_Extended": "0.9",
            "TanimotoCombo": "1.8",
            "pchembl_distance": "0.2",
            "curated_smiles_molecule_a": "CCN",
            "curated_smiles_molecule_b": "CCOO",
        }
    }

    rows = build_modeling_rows(prepared_rows, labels, threshold=0.5)
    numeric_feature_names, categorical_feature_names = build_feature_names(rows)

    assert rows[0]["is_similar"] == 1
    assert rows[0]["atom_count_total"] == 22.0
    assert rows[0]["smiles_length_abs_delta"] == 1.0
    assert rows[0]["element_O_count_b"] == 2.0
    assert rows[0]["element_O_abs_delta"] == 2.0
    assert "element_O_count_b" in numeric_feature_names
    assert categorical_feature_names == ["target_name=CYP2D6"]


def test_train_linear_regression_learns_simple_signal() -> None:
    features = [[0.0], [1.0], [2.0], [3.0]]
    targets = [0.0, 1.0, 2.0, 3.0]

    bias, weights = train_linear_regression(
        features,
        targets,
        learning_rate=0.1,
        epochs=3000,
    )
    predictions = predict(features, bias, weights)

    assert abs(bias) < 0.05
    assert abs(weights[0] - 1.0) < 0.05
    assert (
        max(
            abs(target - prediction)
            for target, prediction in zip(targets, predictions, strict=True)
        )
        < 0.05
    )


def test_train_logistic_regression_learns_binary_signal() -> None:
    features = [[-2.0], [-1.0], [1.0], [2.0]]
    targets = [0, 0, 1, 1]

    bias, weights = train_logistic_regression(features, targets, learning_rate=0.1, epochs=4000)
    probabilities = predict_probabilities(features, bias, weights)

    assert probabilities[0] < 0.2
    assert probabilities[1] < 0.4
    assert probabilities[2] > 0.6
    assert probabilities[3] > 0.8


def test_evaluate_regression_with_threshold_uses_threshold() -> None:
    metrics = evaluate_regression_with_threshold(
        targets=[0.8, 0.2, 0.51, 0.49],
        predictions=[0.7, 0.3, 0.2, 0.8],
        threshold=0.5,
    )

    assert metrics["confusion_matrix"] == {"tp": 1, "tn": 1, "fp": 1, "fn": 1}
    assert metrics["accuracy"] == 0.5


def test_evaluate_probabilities_uses_threshold() -> None:
    metrics = evaluate_probabilities(
        targets=[1, 0, 1, 0],
        probabilities=[0.8, 0.2, 0.4, 0.7],
        threshold=0.5,
    )

    assert metrics["confusion_matrix"] == {"tp": 1, "tn": 1, "fp": 1, "fn": 1}
    assert metrics["accuracy"] == 0.5


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
    assert (reports_dir / "baseline_models.json").exists()
    assert (reports_dir / "baseline_models.md").exists()
