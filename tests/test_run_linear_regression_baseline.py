from scripts.run_linear_regression_baseline import (
    build_feature_names,
    build_modeling_rows,
    evaluate_probabilities,
    evaluate_regression_with_threshold,
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

    bias, weights = train_linear_regression(features, targets, learning_rate=0.1, epochs=3000)
    predictions = predict(features, bias, weights)

    assert abs(bias) < 0.05
    assert abs(weights[0] - 1.0) < 0.05
    assert max(abs(target - prediction) for target, prediction in zip(targets, predictions, strict=True)) < 0.05


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
