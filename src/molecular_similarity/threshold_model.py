from __future__ import annotations

# ruff: noqa: E402

import argparse
import json
from pathlib import Path

from molecular_similarity.linear_regression_baseline import (
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


FEATURE_SET_CANDIDATES = {
    "core_similarity": [
        "tanimoto_cdk_Extended",
        "TanimotoCombo",
        "pchembl_distance",
    ],
    "compact_similarity": [
        "tanimoto_cdk_Extended",
        "TanimotoCombo",
        "pchembl_distance",
        "atom_count_abs_delta",
        "heavy_atom_count_abs_delta",
        "smiles_length_abs_delta",
        "heavy_atom_ratio_gap",
    ],
}
L2_CANDIDATES = [0.1, 0.5]
THRESHOLD_CANDIDATES = [0.45, 0.5, 0.55, 0.6, 0.65]
FOLD_COUNT = 5
TRAINING_EPOCHS = 500
UMAP_RANDOM_STATE = 42
DEFAULT_PREPARED_DATASET_PATH = Path("exploration/reports/prepared_dataset.json")
DEFAULT_LABELS_PATH = Path(
    "/Users/ismailcherkaouiaadil/Downloads/"
    "dataset_Similarity_Prediction/new_dataset/new_dataset.csv"
)
DEFAULT_REPORTS_DIR = Path("exploration/reports")


def _candidate_numeric_features(
    feature_set_name: str,
    all_numeric_feature_names: list[str],
) -> list[str]:
    candidate = FEATURE_SET_CANDIDATES[feature_set_name]
    return list(all_numeric_feature_names if candidate is None else candidate)


def _stratified_folds(
    rows: list[dict[str, object]], fold_count: int = FOLD_COUNT
) -> list[list[dict[str, object]]]:
    positives = sorted(
        [row for row in rows if int(row["is_similar"]) == 1],
        key=lambda row: str(row["pair_id"]),
    )
    negatives = sorted(
        [row for row in rows if int(row["is_similar"]) == 0],
        key=lambda row: str(row["pair_id"]),
    )
    folds = [[] for _ in range(fold_count)]
    for index, row in enumerate(positives):
        folds[index % fold_count].append(row)
    for index, row in enumerate(negatives):
        folds[index % fold_count].append(row)
    for fold in folds:
        fold.sort(key=lambda row: str(row["pair_id"]))
    return folds


def _mean_metric(metrics: list[dict[str, object]], metric_name: str) -> float:
    return sum(float(metric[metric_name]) for metric in metrics) / len(metrics)


def _build_split_features(
    train_rows: list[dict[str, object]],
    eval_rows: list[dict[str, object]],
    numeric_feature_names: list[str],
    categorical_feature_names: list[str],
) -> tuple[list[list[float]], list[int], list[list[float]], list[int]]:
    numeric_stats = compute_numeric_stats(train_rows, numeric_feature_names)
    train_features = [
        vectorize_row(row, numeric_feature_names, categorical_feature_names, numeric_stats)
        for row in train_rows
    ]
    eval_features = [
        vectorize_row(row, numeric_feature_names, categorical_feature_names, numeric_stats)
        for row in eval_rows
    ]
    train_targets = [int(row["is_similar"]) for row in train_rows]
    eval_targets = [int(row["is_similar"]) for row in eval_rows]
    return train_features, train_targets, eval_features, eval_targets


def _evaluate_candidate(
    development_rows: list[dict[str, object]],
    numeric_feature_names: list[str],
    categorical_feature_names: list[str],
    l2_penalty: float,
    threshold: float,
) -> dict[str, object]:
    fold_count = min(FOLD_COUNT, len(development_rows))
    folds = [fold for fold in _stratified_folds(development_rows, fold_count=fold_count) if fold]
    fold_metrics: list[dict[str, object]] = []
    for fold_index, eval_rows in enumerate(folds):
        train_rows = [
            row
            for other_index, fold_rows in enumerate(folds)
            if other_index != fold_index
            for row in fold_rows
        ]
        train_features, train_targets, eval_features, eval_targets = _build_split_features(
            train_rows,
            eval_rows,
            numeric_feature_names,
            categorical_feature_names,
        )
        bias, weights = train_logistic_regression(
            train_features,
            train_targets,
            learning_rate=0.05,
            epochs=TRAINING_EPOCHS,
            l2_penalty=l2_penalty,
        )
        probabilities = predict_probabilities(eval_features, bias, weights)
        fold_metrics.append(evaluate_probabilities(eval_targets, probabilities, threshold=threshold))
    return {
        "mean_accuracy": round(_mean_metric(fold_metrics, "accuracy"), 4),
        "mean_precision": round(_mean_metric(fold_metrics, "precision"), 4),
        "mean_recall": round(_mean_metric(fold_metrics, "recall"), 4),
        "mean_f1": round(_mean_metric(fold_metrics, "f1"), 4),
        "mean_brier_score": round(_mean_metric(fold_metrics, "brier_score"), 4),
        "mean_log_loss": round(_mean_metric(fold_metrics, "log_loss"), 4),
        "fold_metrics": fold_metrics,
    }


def _choose_best_configuration(
    development_rows: list[dict[str, object]],
    all_numeric_feature_names: list[str],
    all_categorical_feature_names: list[str],
) -> dict[str, object]:
    candidate_reports: list[dict[str, object]] = []
    for feature_set_name in FEATURE_SET_CANDIDATES:
        numeric_feature_names = _candidate_numeric_features(
            feature_set_name, all_numeric_feature_names
        )
        for use_target_categories in (False, True):
            categorical_feature_names = list(
                all_categorical_feature_names if use_target_categories else []
            )
            for l2_penalty in L2_CANDIDATES:
                for threshold in THRESHOLD_CANDIDATES:
                    cv_metrics = _evaluate_candidate(
                        development_rows,
                        numeric_feature_names,
                        categorical_feature_names,
                        l2_penalty=l2_penalty,
                        threshold=threshold,
                    )
                    candidate_reports.append(
                        {
                            "feature_set_name": feature_set_name,
                            "use_target_categories": use_target_categories,
                            "threshold": threshold,
                            "l2_penalty": l2_penalty,
                            "numeric_feature_names": numeric_feature_names,
                            "categorical_feature_names": categorical_feature_names,
                            "cv_metrics": cv_metrics,
                        }
                    )
    candidate_reports.sort(
        key=lambda candidate: (
            float(candidate["cv_metrics"]["mean_f1"]),
            float(candidate["cv_metrics"]["mean_accuracy"]),
            -float(candidate["cv_metrics"]["mean_log_loss"]),
            -float(candidate["cv_metrics"]["mean_brier_score"]),
        ),
        reverse=True,
    )
    return candidate_reports[0]


def _all_row_features(
    rows: list[dict[str, object]],
    numeric_feature_names: list[str],
    categorical_feature_names: list[str],
    numeric_stats: dict[str, tuple[float, float]],
) -> list[list[float]]:
    return [
        vectorize_row(row, numeric_feature_names, categorical_feature_names, numeric_stats)
        for row in rows
    ]


def _build_visualization_rows(
    rows: list[dict[str, object]], probabilities: list[float], threshold: float
) -> list[dict[str, object]]:
    visualization_rows: list[dict[str, object]] = []
    for row, probability in zip(rows, probabilities, strict=True):
        visualization_rows.append(
            {
                "pair_id": str(row["pair_id"]),
                "split": str(row["split"]),
                "target_name": str(row["target_name"]),
                "pair_type": str(row["pair_type"]),
                "actual_frac_similar": round(float(row["frac_similar"]), 4),
                "actual_label": int(row["is_similar"]),
                "predicted_probability": round(probability, 4),
                "predicted_label": 1 if probability >= threshold else 0,
            }
        )
    return visualization_rows


def generate_plots(
    report: dict[str, object],
    all_features: list[list[float]],
    plot_rows: list[dict[str, object]],
    reports_dir: Path,
) -> dict[str, str]:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    import umap

    probability_plot_path = reports_dir / "similarity_threshold_model_probability.png"
    umap_plot_path = reports_dir / "similarity_threshold_model_umap.png"
    threshold = float(report["configuration"]["selected_probability_threshold"])

    similar_probabilities = [
        float(row["predicted_probability"]) for row in plot_rows if int(row["actual_label"]) == 1
    ]
    dissimilar_probabilities = [
        float(row["predicted_probability"]) for row in plot_rows if int(row["actual_label"]) == 0
    ]

    plt.style.use("ggplot")
    figure, axis = plt.subplots(figsize=(8, 5))
    axis.hist(dissimilar_probabilities, bins=10, alpha=0.7, label="Actual dissimilar", color="#4C78A8")
    axis.hist(similar_probabilities, bins=10, alpha=0.7, label="Actual similar", color="#F58518")
    axis.axvline(threshold, color="#111111", linestyle="--", linewidth=1.5, label="Decision threshold")
    axis.set_title("Predicted Probability Distribution")
    axis.set_xlabel("Predicted probability of similarity")
    axis.set_ylabel("Pair count")
    axis.legend()
    figure.tight_layout()
    figure.savefig(probability_plot_path, dpi=180)
    plt.close(figure)

    embedding = umap.UMAP(
        n_components=2,
        n_neighbors=min(15, max(2, len(all_features) - 1)),
        min_dist=0.2,
        random_state=UMAP_RANDOM_STATE,
    ).fit_transform(np.array(all_features, dtype=float))

    label_to_color = {0: "#4C78A8", 1: "#F58518"}
    figure, axis = plt.subplots(figsize=(8, 6))
    for actual_label, color in label_to_color.items():
        points = [
            coords
            for coords, row in zip(embedding, plot_rows, strict=True)
            if int(row["actual_label"]) == actual_label
        ]
        if not points:
            continue
        x_values = [float(coords[0]) for coords in points]
        y_values = [float(coords[1]) for coords in points]
        axis.scatter(
            x_values,
            y_values,
            s=55,
            color=color,
            alpha=0.8,
            edgecolors="none",
            label="Similar" if actual_label == 1 else "Dissimilar",
        )
    axis.set_title("UMAP Projection of Molecular Pair Features")
    axis.set_xlabel("UMAP-1")
    axis.set_ylabel("UMAP-2")
    axis.legend(fontsize=8, ncol=2)
    figure.tight_layout()
    figure.savefig(umap_plot_path, dpi=180)
    plt.close(figure)

    return {
        "probability_distribution": probability_plot_path.name,
        "umap_projection": umap_plot_path.name,
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

    all_numeric_feature_names, all_categorical_feature_names = build_feature_names(modeling_rows)
    development_rows = split_to_rows["train"] + split_to_rows["val"]
    selected_configuration = _choose_best_configuration(
        development_rows, all_numeric_feature_names, all_categorical_feature_names
    )
    numeric_feature_names = list(selected_configuration["numeric_feature_names"])
    categorical_feature_names = list(selected_configuration["categorical_feature_names"])
    tuned_threshold = float(selected_configuration["threshold"])
    tuned_l2_penalty = float(selected_configuration["l2_penalty"])
    numeric_stats = compute_numeric_stats(development_rows, numeric_feature_names)

    development_features = _all_row_features(
        development_rows, numeric_feature_names, categorical_feature_names, numeric_stats
    )
    test_features = _all_row_features(
        split_to_rows["test"], numeric_feature_names, categorical_feature_names, numeric_stats
    )
    all_features = _all_row_features(
        modeling_rows, numeric_feature_names, categorical_feature_names, numeric_stats
    )
    development_targets = [int(row["is_similar"]) for row in development_rows]
    test_targets = [int(row["is_similar"]) for row in split_to_rows["test"]]
    bias, weights = train_logistic_regression(
        development_features,
        development_targets,
        learning_rate=0.05,
        epochs=TRAINING_EPOCHS,
        l2_penalty=tuned_l2_penalty,
    )
    development_probabilities = predict_probabilities(development_features, bias, weights)
    test_probabilities = predict_probabilities(test_features, bias, weights)
    all_probabilities = predict_probabilities(all_features, bias, weights)

    test_examples = [
        {
            "pair_id": row["pair_id"],
            "target_name": row["target_name"],
            "pair_type": row["pair_type"],
            "actual_frac_similar": round(float(row["frac_similar"]), 4),
            "actual_label": int(row["is_similar"]),
            "predicted_probability": round(probability, 4),
            "predicted_label": 1 if probability >= tuned_threshold else 0,
        }
        for row, probability in zip(split_to_rows["test"], test_probabilities, strict=True)
    ]

    plot_rows = _build_visualization_rows(modeling_rows, all_probabilities, tuned_threshold)
    return {
        "configuration": {
            "prepared_dataset_path": str(prepared_dataset_path),
            "labels_path": str(labels_path),
            "label_threshold": threshold,
            "selected_probability_threshold": tuned_threshold,
            "selected_l2_penalty": tuned_l2_penalty,
            "selected_feature_set": selected_configuration["feature_set_name"],
            "selected_use_target_categories": selected_configuration["use_target_categories"],
            "numeric_feature_count": len(numeric_feature_names),
            "categorical_feature_count": len(categorical_feature_names),
            "numeric_features": numeric_feature_names,
            "categorical_features": categorical_feature_names,
        },
        "dataset": {
            "row_count": len(modeling_rows),
            "split_counts": {split_name: len(rows) for split_name, rows in split_to_rows.items()},
        },
        "model_selection": {
            "fold_count": FOLD_COUNT,
            "candidate_feature_sets": list(FEATURE_SET_CANDIDATES),
            "candidate_l2_penalties": L2_CANDIDATES,
            "candidate_thresholds": THRESHOLD_CANDIDATES,
            "selected_configuration": {
                "feature_set_name": selected_configuration["feature_set_name"],
                "use_target_categories": selected_configuration["use_target_categories"],
                "threshold": tuned_threshold,
                "l2_penalty": tuned_l2_penalty,
                "cv_metrics": selected_configuration["cv_metrics"],
            },
        },
        "model": {
            "name": "cross_validated_logistic_threshold_classifier",
            "metrics": {
                "development": evaluate_probabilities(
                    development_targets, development_probabilities, threshold=tuned_threshold
                ),
                "test": evaluate_probabilities(
                    test_targets, test_probabilities, threshold=tuned_threshold
                ),
            },
            "coefficients": {
                "bias": round(bias, 6),
                "weights": {
                    feature_name: round(weight, 6)
                    for feature_name, weight in zip(
                        numeric_feature_names + categorical_feature_names, weights, strict=True
                    )
                },
            },
        },
        "plots": {},
        "visualization_features": all_features,
        "visualization_rows": plot_rows,
        "test_examples": test_examples,
    }


def render_markdown(report: dict[str, object]) -> str:
    cv_metrics = report["model_selection"]["selected_configuration"]["cv_metrics"]
    lines = [
        "# Threshold-Based Similarity Model",
        "",
        f"- Similarity label threshold: {report['configuration']['label_threshold']}",
        (
            "- Selected probability threshold: "
            f"{report['configuration']['selected_probability_threshold']}"
        ),
        f"- Selected feature set: {report['configuration']['selected_feature_set']}",
        f"- Selected L2 penalty: {report['configuration']['selected_l2_penalty']}",
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
        "## Model Selection",
        "",
        (
            "- Cross-validation summary: "
            f"folds={report['model_selection']['fold_count']}, "
            f"mean_f1={cv_metrics['mean_f1']}, "
            f"mean_accuracy={cv_metrics['mean_accuracy']}, "
            f"mean_log_loss={cv_metrics['mean_log_loss']}"
        ),
        "",
        "## Classification Metrics",
        "",
        "| split | log_loss | brier | accuracy | precision | recall | f1 |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for split_name in ("development", "test"):
        metrics = report["model"]["metrics"][split_name]
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
    if report.get("plots"):
        lines.extend(
            [
                "",
                "## Plots",
                "",
                "### Probability Distribution",
                "",
                (
                    "![Predicted probability distribution]"
                    f"({report['plots']['probability_distribution']})"
                ),
                "",
                "### UMAP Projection",
                "",
                (
                    "The UMAP view projects molecule-pair feature vectors into 2D; "
                    "colors show actual similarity labels."
                ),
                "",
                (
                    "![UMAP projection of molecular pair features]"
                    f"({report['plots']['umap_projection']})"
                ),
            ]
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


def write_report(report: dict[str, object], reports_dir: Path = DEFAULT_REPORTS_DIR) -> tuple[Path, Path]:
    reports_dir.mkdir(parents=True, exist_ok=True)
    json_path = reports_dir / "similarity_threshold_model.json"
    markdown_path = reports_dir / "similarity_threshold_model.md"
    report["plots"] = generate_plots(
        report, report["visualization_features"], report["visualization_rows"], reports_dir
    )
    del report["visualization_features"]
    del report["visualization_rows"]
    json_path.write_text(json.dumps(report, indent=2))
    markdown_path.write_text(render_markdown(report))
    return json_path, markdown_path


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Train and report the threshold-based molecular similarity classifier."
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
        "label_threshold",
        nargs="?",
        default=str(DEFAULT_THRESHOLD),
        help=f"Similarity label threshold (default: {DEFAULT_THRESHOLD})",
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
    report = build_report(
        prepared_dataset_path, labels_path, threshold=float(args.label_threshold)
    )
    json_path, markdown_path = write_report(
        report, reports_dir=Path(args.reports_dir).expanduser().resolve()
    )
    test_metrics = report["model"]["metrics"]["test"]
    print(f"Wrote {json_path}")
    print(f"Wrote {markdown_path}")
    print(
        "Selected config: "
        f"feature_set={report['configuration']['selected_feature_set']}, "
        f"probability_threshold={report['configuration']['selected_probability_threshold']}, "
        f"l2_penalty={report['configuration']['selected_l2_penalty']}"
    )
    print(f"Test accuracy: {test_metrics['accuracy']}")
    print(f"Test f1: {test_metrics['f1']}")
    print(f"Test log loss: {test_metrics['log_loss']}")
    return 0
