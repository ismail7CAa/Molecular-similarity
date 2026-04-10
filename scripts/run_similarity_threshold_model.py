from __future__ import annotations

import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from scripts.run_linear_regression_baseline import (
    DEFAULT_THRESHOLD,
    build_feature_names,
    build_modeling_rows,
    compute_numeric_stats,
    evaluate_probabilities,
    load_prepared_rows,
    load_similarity_labels,
    predict_probabilities,
    split_rows,
    train_logistic_regression,
    vectorize_row,
)


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

    split_features = {
        split_name: [
            vectorize_row(row, numeric_feature_names, categorical_feature_names, numeric_stats)
            for row in rows
        ]
        for split_name, rows in split_to_rows.items()
    }
    split_targets = {
        split_name: [int(row["is_similar"]) for row in rows]
        for split_name, rows in split_to_rows.items()
    }

    bias, weights = train_logistic_regression(split_features["train"], split_targets["train"])
    split_probabilities = {
        split_name: predict_probabilities(features, bias, weights)
        for split_name, features in split_features.items()
    }

    test_examples = []
    for row, probability in zip(
        split_to_rows["test"],
        split_probabilities["test"],
        strict=True,
    ):
        test_examples.append(
            {
                "pair_id": row["pair_id"],
                "target_name": row["target_name"],
                "pair_type": row["pair_type"],
                "actual_frac_similar": round(float(row["frac_similar"]), 4),
                "actual_label": int(row["is_similar"]),
                "predicted_probability": round(probability, 4),
                "predicted_label": 1 if probability >= threshold else 0,
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
            "split_counts": {split_name: len(rows) for split_name, rows in split_to_rows.items()},
        },
        "model": {
            "name": "logistic_regression_threshold_classifier",
            "metrics": {
                split_name: evaluate_probabilities(
                    split_targets[split_name],
                    split_probabilities[split_name],
                    threshold=threshold,
                )
                for split_name in ("train", "val", "test")
            },
            "coefficients": {
                "bias": round(bias, 6),
                "weights": {
                    feature_name: round(weight, 6)
                    for feature_name, weight in zip(
                        numeric_feature_names + categorical_feature_names,
                        weights,
                        strict=True,
                    )
                },
            },
        },
        "test_examples": test_examples,
    }


def render_markdown(report: dict[str, object]) -> str:
    lines = [
        "# Threshold-Based Similarity Model",
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
        "## Classification Metrics",
        "",
        "| split | log_loss | brier | accuracy | precision | recall | f1 |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]

    for split_name in ("train", "val", "test"):
        metrics = report["model"]["metrics"][split_name]
        lines.append(
            "| {split_name} | {log_loss} | {brier_score} | {accuracy} | {precision} | {recall} | {f1} |".format(
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
            "| pair_id | target | type | frac_similar | actual_label | probability | predicted_label |",
            "| --- | --- | --- | ---: | ---: | ---: | ---: |",
        ]
    )

    for example in report["test_examples"]:
        lines.append(
            "| {pair_id} | {target_name} | {pair_type} | {actual_frac_similar} | "
            "{actual_label} | {predicted_probability} | {predicted_label} |".format(
                **example
            )
        )

    return "\n".join(lines) + "\n"


def main() -> int:
    prepared_dataset_path = Path("exploration/reports/prepared_dataset.json")
    labels_path = Path(
        "/Users/ismailcherkaouiaadil/Downloads/dataset_Similarity_Prediction/new_dataset/new_dataset.csv"
    )

    if len(sys.argv) not in {1, 3, 4}:
        print(
            "Usage: python scripts/run_similarity_threshold_model.py "
            "[prepared_dataset.json labels.csv [threshold]]"
        )
        return 1

    if len(sys.argv) >= 3:
        prepared_dataset_path = Path(sys.argv[1]).expanduser().resolve()
        labels_path = Path(sys.argv[2]).expanduser().resolve()

    threshold = float(sys.argv[3]) if len(sys.argv) == 4 else DEFAULT_THRESHOLD
    report = build_report(prepared_dataset_path, labels_path, threshold=threshold)

    reports_dir = Path("exploration/reports")
    reports_dir.mkdir(parents=True, exist_ok=True)
    json_path = reports_dir / "similarity_threshold_model.json"
    markdown_path = reports_dir / "similarity_threshold_model.md"

    json_path.write_text(json.dumps(report, indent=2))
    markdown_path.write_text(render_markdown(report))

    test_metrics = report["model"]["metrics"]["test"]
    print(f"Wrote {json_path}")
    print(f"Wrote {markdown_path}")
    print(f"Test accuracy: {test_metrics['accuracy']}")
    print(f"Test f1: {test_metrics['f1']}")
    print(f"Test log loss: {test_metrics['log_loss']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
