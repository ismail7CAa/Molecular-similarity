from __future__ import annotations

import csv
import json
import math
import argparse
from pathlib import Path

DEFAULT_THRESHOLD = 0.5
DEFAULT_PREPARED_DATASET_PATH = Path("exploration/reports/prepared_dataset.json")
DEFAULT_LABELS_PATH = Path(
    "/Users/ismailcherkaouiaadil/Downloads/"
    "dataset_Similarity_Prediction/new_dataset/new_dataset.csv"
)
DEFAULT_REPORTS_DIR = Path("exploration/reports")
BASE_NUMERIC_FEATURES = [
    "atom_count_a",
    "atom_count_b",
    "heavy_atom_count_a",
    "heavy_atom_count_b",
    "atom_count_delta",
    "heavy_atom_count_delta",
    "atom_count_total",
    "heavy_atom_count_total",
    "atom_count_abs_delta",
    "heavy_atom_count_abs_delta",
    "heavy_atom_ratio_a",
    "heavy_atom_ratio_b",
    "heavy_atom_ratio_gap",
    "smiles_length_a",
    "smiles_length_b",
    "smiles_length_delta",
    "smiles_length_abs_delta",
    "tanimoto_cdk_Extended",
    "TanimotoCombo",
    "pchembl_distance",
]


def load_prepared_rows(path: Path) -> list[dict[str, object]]:
    payload = json.loads(path.read_text())
    return list(payload["rows"])


def load_similarity_labels(path: Path) -> dict[str, dict[str, str]]:
    with path.open() as handle:
        reader = csv.DictReader(handle)
        return {f"{int(row['id_pair']):03d}": row for row in reader}


def _safe_ratio(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def _load_element_counts(raw_value: object) -> dict[str, int]:
    if isinstance(raw_value, str):
        parsed = json.loads(raw_value)
        return {str(key): int(value) for key, value in parsed.items()}
    return {}


def build_modeling_rows(
    prepared_rows: list[dict[str, object]],
    similarity_labels: dict[str, dict[str, str]],
    threshold: float = DEFAULT_THRESHOLD,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []

    for prepared_row in prepared_rows:
        pair_id = str(prepared_row["pair_id"])
        label_row = similarity_labels[pair_id]
        frac_similar = float(label_row["frac_similar"])
        atom_count_a = float(prepared_row["atom_count_a"])
        atom_count_b = float(prepared_row["atom_count_b"])
        heavy_atom_count_a = float(prepared_row["heavy_atom_count_a"])
        heavy_atom_count_b = float(prepared_row["heavy_atom_count_b"])
        smiles_a = str(label_row["curated_smiles_molecule_a"])
        smiles_b = str(label_row["curated_smiles_molecule_b"])
        element_counts_a = _load_element_counts(prepared_row["element_counts_a"])
        element_counts_b = _load_element_counts(prepared_row["element_counts_b"])

        row: dict[str, object] = {
            "pair_id": pair_id,
            "split": str(prepared_row["split"]),
            "target_name": label_row["target_name"],
            "pair_type": label_row["pair_type"],
            "frac_similar": frac_similar,
            "is_similar": 1 if frac_similar >= threshold else 0,
            "atom_count_a": atom_count_a,
            "atom_count_b": atom_count_b,
            "heavy_atom_count_a": heavy_atom_count_a,
            "heavy_atom_count_b": heavy_atom_count_b,
            "atom_count_delta": float(prepared_row["atom_count_delta"]),
            "heavy_atom_count_delta": float(prepared_row["heavy_atom_count_delta"]),
            "atom_count_total": atom_count_a + atom_count_b,
            "heavy_atom_count_total": heavy_atom_count_a + heavy_atom_count_b,
            "atom_count_abs_delta": abs(atom_count_a - atom_count_b),
            "heavy_atom_count_abs_delta": abs(heavy_atom_count_a - heavy_atom_count_b),
            "heavy_atom_ratio_a": _safe_ratio(heavy_atom_count_a, atom_count_a),
            "heavy_atom_ratio_b": _safe_ratio(heavy_atom_count_b, atom_count_b),
            "heavy_atom_ratio_gap": abs(
                _safe_ratio(heavy_atom_count_a, atom_count_a)
                - _safe_ratio(heavy_atom_count_b, atom_count_b)
            ),
            "smiles_length_a": float(len(smiles_a)),
            "smiles_length_b": float(len(smiles_b)),
            "smiles_length_delta": float(len(smiles_b) - len(smiles_a)),
            "smiles_length_abs_delta": float(abs(len(smiles_b) - len(smiles_a))),
            "tanimoto_cdk_Extended": float(label_row["tanimoto_cdk_Extended"]),
            "TanimotoCombo": float(label_row["TanimotoCombo"]),
            "pchembl_distance": float(label_row["pchembl_distance"]),
        }

        all_elements = sorted(set(element_counts_a) | set(element_counts_b))
        for element in all_elements:
            count_a = float(element_counts_a.get(element, 0))
            count_b = float(element_counts_b.get(element, 0))
            row[f"element_{element}_count_a"] = count_a
            row[f"element_{element}_count_b"] = count_b
            row[f"element_{element}_delta"] = count_b - count_a
            row[f"element_{element}_abs_delta"] = abs(count_b - count_a)

        rows.append(row)

    return rows


def build_feature_names(rows: list[dict[str, object]]) -> tuple[list[str], list[str]]:
    numeric_feature_names = set(BASE_NUMERIC_FEATURES)
    for row in rows:
        for key, value in row.items():
            if key.startswith("element_") and isinstance(value, float):
                numeric_feature_names.add(key)

    categorical_feature_names = [
        f"target_name={target_name}"
        for target_name in sorted({str(row["target_name"]) for row in rows})
    ]

    return sorted(numeric_feature_names), categorical_feature_names


def compute_numeric_stats(
    rows: list[dict[str, object]], numeric_feature_names: list[str]
) -> dict[str, tuple[float, float]]:
    stats: dict[str, tuple[float, float]] = {}

    for feature_name in numeric_feature_names:
        values = [float(row.get(feature_name, 0.0)) for row in rows]
        mean_value = sum(values) / len(values)
        variance = sum((value - mean_value) ** 2 for value in values) / len(values)
        std_value = math.sqrt(variance)
        stats[feature_name] = (
            mean_value,
            std_value if std_value > 0 else 1.0,
        )

    return stats


def vectorize_row(
    row: dict[str, object],
    numeric_feature_names: list[str],
    categorical_feature_names: list[str],
    numeric_stats: dict[str, tuple[float, float]],
) -> list[float]:
    values: list[float] = []

    for feature_name in numeric_feature_names:
        mean_value, std_value = numeric_stats[feature_name]
        numeric_value = float(row.get(feature_name, 0.0))
        values.append((numeric_value - mean_value) / std_value)

    for feature_name in categorical_feature_names:
        target_name = feature_name.split("=", maxsplit=1)[1]
        values.append(1.0 if str(row["target_name"]) == target_name else 0.0)

    return values


def train_linear_regression(
    feature_matrix: list[list[float]],
    targets: list[float],
    learning_rate: float = 0.05,
    epochs: int = 6000,
    l2_penalty: float = 1e-4,
) -> tuple[float, list[float]]:
    if not feature_matrix:
        raise ValueError("feature_matrix must not be empty")

    feature_count = len(feature_matrix[0])
    weights = [0.0] * feature_count
    bias = 0.0
    sample_count = len(feature_matrix)

    for _ in range(epochs):
        bias_gradient = 0.0
        weight_gradients = [0.0] * feature_count

        for features, target in zip(feature_matrix, targets, strict=True):
            prediction = bias + sum(
                weight * value
                for weight, value in zip(weights, features, strict=True)
            )
            error = prediction - target
            bias_gradient += error
            for index, feature_value in enumerate(features):
                weight_gradients[index] += error * feature_value

        bias -= learning_rate * (2.0 * bias_gradient / sample_count)
        for index in range(feature_count):
            regularized_gradient = (2.0 * weight_gradients[index] / sample_count) + (
                2.0 * l2_penalty * weights[index]
            )
            weights[index] -= learning_rate * regularized_gradient

    return bias, weights


def _sigmoid(value: float) -> float:
    clipped_value = max(min(value, 35.0), -35.0)
    return 1.0 / (1.0 + math.exp(-clipped_value))


def train_logistic_regression(
    feature_matrix: list[list[float]],
    targets: list[int],
    learning_rate: float = 0.05,
    epochs: int = 6000,
    l2_penalty: float = 1e-4,
) -> tuple[float, list[float]]:
    if not feature_matrix:
        raise ValueError("feature_matrix must not be empty")

    feature_count = len(feature_matrix[0])
    weights = [0.0] * feature_count
    bias = 0.0
    sample_count = len(feature_matrix)

    for _ in range(epochs):
        bias_gradient = 0.0
        weight_gradients = [0.0] * feature_count

        for features, target in zip(feature_matrix, targets, strict=True):
            score = bias + sum(
                weight * value
                for weight, value in zip(weights, features, strict=True)
            )
            probability = _sigmoid(score)
            error = probability - float(target)
            bias_gradient += error
            for index, feature_value in enumerate(features):
                weight_gradients[index] += error * feature_value

        bias -= learning_rate * (bias_gradient / sample_count)
        for index in range(feature_count):
            regularized_gradient = (weight_gradients[index] / sample_count) + (
                2.0 * l2_penalty * weights[index]
            )
            weights[index] -= learning_rate * regularized_gradient

    return bias, weights


def predict(
    feature_matrix: list[list[float]],
    bias: float,
    weights: list[float],
) -> list[float]:
    return [
        bias + sum(weight * value for weight, value in zip(weights, features, strict=True))
        for features in feature_matrix
    ]


def predict_probabilities(
    feature_matrix: list[list[float]],
    bias: float,
    weights: list[float],
) -> list[float]:
    return [_sigmoid(score) for score in predict(feature_matrix, bias, weights)]


def evaluate_threshold_predictions(
    targets: list[int], scores: list[float], threshold: float = DEFAULT_THRESHOLD
) -> dict[str, object]:
    if len(targets) != len(scores):
        raise ValueError("targets and scores must have the same length")

    binary_predictions = [1 if score >= threshold else 0 for score in scores]
    true_positive = sum(
        1
        for target, prediction in zip(targets, binary_predictions, strict=True)
        if target == 1 and prediction == 1
    )
    true_negative = sum(
        1
        for target, prediction in zip(targets, binary_predictions, strict=True)
        if target == 0 and prediction == 0
    )
    false_positive = sum(
        1
        for target, prediction in zip(targets, binary_predictions, strict=True)
        if target == 0 and prediction == 1
    )
    false_negative = sum(
        1
        for target, prediction in zip(targets, binary_predictions, strict=True)
        if target == 1 and prediction == 0
    )

    accuracy = (true_positive + true_negative) / len(targets)
    precision = (
        true_positive / (true_positive + false_positive)
        if (true_positive + false_positive)
        else 0.0
    )
    recall = (
        true_positive / (true_positive + false_negative)
        if (true_positive + false_negative)
        else 0.0
    )
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0

    return {
        "sample_count": len(targets),
        "accuracy": round(accuracy, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "confusion_matrix": {
            "tp": true_positive,
            "tn": true_negative,
            "fp": false_positive,
            "fn": false_negative,
        },
    }


def evaluate_regression_with_threshold(
    targets: list[float], predictions: list[float], threshold: float = DEFAULT_THRESHOLD
) -> dict[str, object]:
    binary_targets = [1 if target >= threshold else 0 for target in targets]
    mse = sum(
        (target - prediction) ** 2 for target, prediction in zip(targets, predictions, strict=True)
    ) / len(targets)
    mae = sum(
        abs(target - prediction) for target, prediction in zip(targets, predictions, strict=True)
    ) / len(targets)
    classification = evaluate_threshold_predictions(
        binary_targets,
        predictions,
        threshold=threshold,
    )

    return {
        **classification,
        "mse": round(mse, 4),
        "mae": round(mae, 4),
    }


def evaluate_probabilities(
    targets: list[int], probabilities: list[float], threshold: float = DEFAULT_THRESHOLD
) -> dict[str, object]:
    brier = sum(
        (float(target) - probability) ** 2
        for target, probability in zip(targets, probabilities, strict=True)
    ) / len(targets)
    log_loss = 0.0
    for target, probability in zip(targets, probabilities, strict=True):
        clipped_probability = min(max(probability, 1e-9), 1 - 1e-9)
        log_loss += -(
            float(target) * math.log(clipped_probability)
            + (1.0 - float(target)) * math.log(1.0 - clipped_probability)
        )
    log_loss /= len(targets)

    classification = evaluate_threshold_predictions(targets, probabilities, threshold=threshold)
    return {
        **classification,
        "brier_score": round(brier, 4),
        "log_loss": round(log_loss, 4),
    }


def split_rows(rows: list[dict[str, object]]) -> dict[str, list[dict[str, object]]]:
    result = {"train": [], "val": [], "test": []}
    for row in rows:
        result[str(row["split"])].append(row)
    return result


def _coefficients_dict(
    bias: float,
    weights: list[float],
    numeric_feature_names: list[str],
    categorical_feature_names: list[str],
) -> dict[str, object]:
    feature_names = numeric_feature_names + categorical_feature_names
    return {
        "bias": round(bias, 6),
        "weights": {
            feature_name: round(weight, 6)
            for feature_name, weight in zip(feature_names, weights, strict=True)
        },
    }


def build_report(
    prepared_dataset_path: Path,
    labels_path: Path,
    threshold: float = DEFAULT_THRESHOLD,
) -> dict[str, object]:
    prepared_rows = load_prepared_rows(prepared_dataset_path)
    similarity_labels = load_similarity_labels(labels_path)
    modeling_rows = build_modeling_rows(prepared_rows, similarity_labels, threshold=threshold)
    split_to_rows = split_rows(modeling_rows)

    numeric_feature_names, categorical_feature_names = build_feature_names(modeling_rows)
    numeric_stats = compute_numeric_stats(split_to_rows["train"], numeric_feature_names)

    train_features = [
        vectorize_row(row, numeric_feature_names, categorical_feature_names, numeric_stats)
        for row in split_to_rows["train"]
    ]
    val_features = [
        vectorize_row(row, numeric_feature_names, categorical_feature_names, numeric_stats)
        for row in split_to_rows["val"]
    ]
    test_features = [
        vectorize_row(row, numeric_feature_names, categorical_feature_names, numeric_stats)
        for row in split_to_rows["test"]
    ]

    train_frac_targets = [float(row["frac_similar"]) for row in split_to_rows["train"]]
    val_frac_targets = [float(row["frac_similar"]) for row in split_to_rows["val"]]
    test_frac_targets = [float(row["frac_similar"]) for row in split_to_rows["test"]]
    train_binary_targets = [int(row["is_similar"]) for row in split_to_rows["train"]]
    val_binary_targets = [int(row["is_similar"]) for row in split_to_rows["val"]]
    test_binary_targets = [int(row["is_similar"]) for row in split_to_rows["test"]]

    linear_bias, linear_weights = train_linear_regression(train_features, train_frac_targets)
    linear_train_predictions = predict(train_features, linear_bias, linear_weights)
    linear_val_predictions = predict(val_features, linear_bias, linear_weights)
    linear_test_predictions = predict(test_features, linear_bias, linear_weights)

    logistic_bias, logistic_weights = train_logistic_regression(
        train_features,
        train_binary_targets,
    )
    logistic_train_probabilities = predict_probabilities(
        train_features,
        logistic_bias,
        logistic_weights,
    )
    logistic_val_probabilities = predict_probabilities(
        val_features,
        logistic_bias,
        logistic_weights,
    )
    logistic_test_probabilities = predict_probabilities(
        test_features,
        logistic_bias,
        logistic_weights,
    )

    test_examples = []
    for row, linear_prediction, logistic_probability in zip(
        split_to_rows["test"],
        linear_test_predictions,
        logistic_test_probabilities,
        strict=True,
    ):
        test_examples.append(
            {
                "pair_id": row["pair_id"],
                "target_name": row["target_name"],
                "pair_type": row["pair_type"],
                "actual_frac_similar": round(float(row["frac_similar"]), 4),
                "actual_label": int(row["is_similar"]),
                "linear_prediction": round(linear_prediction, 4),
                "linear_label": 1 if linear_prediction >= threshold else 0,
                "logistic_probability": round(logistic_probability, 4),
                "logistic_label": 1 if logistic_probability >= threshold else 0,
            }
        )

    return {
        "configuration": {
            "prepared_dataset_path": str(prepared_dataset_path),
            "labels_path": str(labels_path),
            "threshold": threshold,
            "numeric_feature_count": len(numeric_feature_names),
            "categorical_feature_count": len(categorical_feature_names),
            "numeric_features": numeric_feature_names,
            "categorical_features": categorical_feature_names,
        },
        "dataset": {
            "row_count": len(modeling_rows),
            "split_counts": {
                split_name: len(rows) for split_name, rows in split_to_rows.items()
            },
        },
        "models": {
            "linear_regression": {
                "metrics": {
                    "train": evaluate_regression_with_threshold(
                        train_frac_targets, linear_train_predictions, threshold=threshold
                    ),
                    "val": evaluate_regression_with_threshold(
                        val_frac_targets, linear_val_predictions, threshold=threshold
                    ),
                    "test": evaluate_regression_with_threshold(
                        test_frac_targets, linear_test_predictions, threshold=threshold
                    ),
                },
                "coefficients": _coefficients_dict(
                    linear_bias,
                    linear_weights,
                    numeric_feature_names,
                    categorical_feature_names,
                ),
            },
            "logistic_regression": {
                "metrics": {
                    "train": evaluate_probabilities(
                        train_binary_targets, logistic_train_probabilities, threshold=threshold
                    ),
                    "val": evaluate_probabilities(
                        val_binary_targets, logistic_val_probabilities, threshold=threshold
                    ),
                    "test": evaluate_probabilities(
                        test_binary_targets, logistic_test_probabilities, threshold=threshold
                    ),
                },
                "coefficients": _coefficients_dict(
                    logistic_bias,
                    logistic_weights,
                    numeric_feature_names,
                    categorical_feature_names,
                ),
            },
        },
        "test_examples": test_examples,
    }


def render_markdown(report: dict[str, object]) -> str:
    lines = [
        "# Baseline Models",
        "",
        f"- Decision threshold: {report['configuration']['threshold']}",
        f"- Rows: {report['dataset']['row_count']}",
        (
            "- Feature counts: "
            f"numeric={report['configuration']['numeric_feature_count']}, "
            f"categorical={report['configuration']['categorical_feature_count']}"
        ),
        (
            "- Split counts: "
            + ", ".join(
                f"{split_name}={count}"
                for split_name, count in report["dataset"]["split_counts"].items()
            )
        ),
        "",
        "## Linear Regression",
        "",
        "| split | mse | mae | accuracy | precision | recall | f1 |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]

    for split_name in ("train", "val", "test"):
        metrics = report["models"]["linear_regression"]["metrics"][split_name]
        lines.append(
            "| {split_name} | {mse} | {mae} | {accuracy} | {precision} | {recall} | {f1} |".format(
                split_name=split_name,
                mse=metrics["mse"],
                mae=metrics["mae"],
                accuracy=metrics["accuracy"],
                precision=metrics["precision"],
                recall=metrics["recall"],
                f1=metrics["f1"],
            )
        )

    lines.extend(
        [
            "",
            "## Logistic Regression",
            "",
            "| split | log_loss | brier | accuracy | precision | recall | f1 |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )

    for split_name in ("train", "val", "test"):
        metrics = report["models"]["logistic_regression"]["metrics"][split_name]
        lines.append(
            (
                "| {split_name} | {log_loss} | {brier_score} | {accuracy} | "
                "{precision} | {recall} | {f1} |"
            ).format(
                split_name=split_name,
                log_loss=metrics["log_loss"],
                brier_score=metrics["brier_score"],
                accuracy=metrics["accuracy"],
                precision=metrics["precision"],
                recall=metrics["recall"],
                f1=metrics["f1"],
            )
        )

    lines.extend(
        [
            "",
            "## Test Predictions",
            "",
            "| pair_id | target | type | actual | linear | logistic | actual_label |",
            "| --- | --- | --- | ---: | ---: | ---: | ---: |",
        ]
    )

    for example in report["test_examples"]:
        lines.append(
            "| {pair_id} | {target_name} | {pair_type} | {actual_frac_similar} | "
            "{linear_prediction} | {logistic_probability} | {actual_label} |".format(
                **example
            )
        )

    return "\n".join(lines) + "\n"


def write_report(report: dict[str, object], reports_dir: Path = DEFAULT_REPORTS_DIR) -> tuple[Path, Path]:
    reports_dir.mkdir(parents=True, exist_ok=True)
    json_path = reports_dir / "baseline_models.json"
    markdown_path = reports_dir / "baseline_models.md"
    json_path.write_text(json.dumps(report, indent=2))
    markdown_path.write_text(render_markdown(report))
    return json_path, markdown_path


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Train and report the baseline molecular similarity models."
    )
    parser.add_argument(
        "prepared_dataset_path",
        nargs="?",
        default=str(DEFAULT_PREPARED_DATASET_PATH),
        help=f"Prepared dataset JSON path (default: {DEFAULT_PREPARED_DATASET_PATH})",
    )
    parser.add_argument(
        "labels_path",
        nargs="?",
        default=str(DEFAULT_LABELS_PATH),
        help=f"Similarity labels CSV path (default: {DEFAULT_LABELS_PATH})",
    )
    parser.add_argument(
        "threshold",
        nargs="?",
        type=float,
        default=DEFAULT_THRESHOLD,
        help=f"Decision threshold (default: {DEFAULT_THRESHOLD})",
    )
    parser.add_argument(
        "--reports-dir",
        default=str(DEFAULT_REPORTS_DIR),
        help=f"Directory for JSON/Markdown reports (default: {DEFAULT_REPORTS_DIR})",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    prepared_dataset_path = Path(args.prepared_dataset_path).expanduser().resolve()
    labels_path = Path(args.labels_path).expanduser().resolve()
    threshold = float(args.threshold)
    reports_dir = Path(args.reports_dir).expanduser().resolve()

    report = build_report(prepared_dataset_path, labels_path, threshold=threshold)
    json_path, markdown_path = write_report(report, reports_dir=reports_dir)

    linear_test = report["models"]["linear_regression"]["metrics"]["test"]
    logistic_test = report["models"]["logistic_regression"]["metrics"]["test"]
    print(f"Wrote {json_path}")
    print(f"Wrote {markdown_path}")
    print(f"Linear test accuracy: {linear_test['accuracy']}")
    print(f"Linear test f1: {linear_test['f1']}")
    print(f"Logistic test accuracy: {logistic_test['accuracy']}")
    print(f"Logistic test f1: {logistic_test['f1']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
