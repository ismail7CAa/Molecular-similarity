from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib
from sklearn.linear_model import LinearRegression, LogisticRegression

from molecular_similarity.linear_regression_baseline import (
    evaluate_probabilities,
    evaluate_regression_with_threshold,
)
from molecular_similarity.metrics import auroc_score, roc_curve_points
from molecular_similarity.sql_activity_model import (
    DEFAULT_EXPORT_PATH,
    DEFAULT_REPORTS_DIR,
    choose_best_configuration,
    compute_numeric_stats,
    load_rows,
    split_rows,
    vectorize_row,
)

matplotlib.use("Agg")
from matplotlib import pyplot as plt


def _with_auroc(
    metrics: dict[str, object], targets: list[int], scores: list[float]
) -> dict[str, object]:
    return {**metrics, "auroc": auroc_score(targets, scores)}


def _curve_points(targets: list[int], scores: list[float]) -> list[dict[str, float]]:
    return [
        {
            "false_positive_rate": round(point["false_positive_rate"], 6),
            "true_positive_rate": round(point["true_positive_rate"], 6),
        }
        for point in roc_curve_points(targets, scores)
    ]


def _plot_auroc_curve(
    curve_points: list[dict[str, float]],
    auroc: float | None,
    output_path: Path,
    title: str,
    color: str,
) -> None:
    figure, axis = plt.subplots(figsize=(7, 6))
    if curve_points:
        x_values = [float(point["false_positive_rate"]) for point in curve_points]
        y_values = [float(point["true_positive_rate"]) for point in curve_points]
        axis.step(x_values, y_values, where="post", color=color, linewidth=2.4, label="Model ROC")
        axis.fill_between(
            x_values,
            y_values,
            step="post",
            color=color,
            alpha=0.16,
            label="AUROC area",
        )
    axis.plot([0, 1], [0, 1], color="#6b7280", linestyle="--", linewidth=1.1, label="Chance")
    axis.set_xlim(0.0, 1.0)
    axis.set_ylim(0.0, 1.0)
    axis.set_xlabel("False positive rate")
    axis.set_ylabel("True positive rate")
    axis.set_title(f"{title}\nAUROC={auroc if auroc is not None else 'N/A'}")
    axis.grid(linestyle="--", alpha=0.3)
    axis.legend(frameon=False, loc="lower right")
    figure.tight_layout()
    figure.savefig(output_path, dpi=220, bbox_inches="tight")
    plt.close(figure)


def generate_plots(report: dict[str, object], reports_dir: Path) -> dict[str, str]:
    linear_path = reports_dir / "chembl_linear_model_auroc.png"
    logistic_path = reports_dir / "chembl_logistic_model_auroc.png"
    _plot_auroc_curve(
        list(report["auroc_curves"]["linear_regression"]["test"]),
        report["models"]["linear_regression"]["metrics"]["test"]["auroc"],
        linear_path,
        "ChEMBL Linear Regression ROC on Test Split",
        "#2563eb",
    )
    _plot_auroc_curve(
        list(report["auroc_curves"]["logistic_regression"]["test"]),
        report["models"]["logistic_regression"]["metrics"]["test"]["auroc"],
        logistic_path,
        "ChEMBL Logistic Regression ROC on Test Split",
        "#f97316",
    )
    return {
        "linear_auroc_curve": linear_path.name,
        "logistic_auroc_curve": logistic_path.name,
    }


def build_report(export_path: Path) -> dict[str, object]:
    rows = load_rows(export_path)
    split_to_rows = split_rows(rows)
    selected = choose_best_configuration(rows)
    numeric_feature_names = list(selected["numeric_feature_names"])
    categorical_feature_names = list(selected["categorical_feature_names"])
    numeric_stats = compute_numeric_stats(
        split_to_rows["train"] + split_to_rows["val"], numeric_feature_names
    )
    development_rows = split_to_rows["train"] + split_to_rows["val"]
    test_rows = split_to_rows["test"]
    development_features = [
        vectorize_row(row, numeric_feature_names, categorical_feature_names, numeric_stats)
        for row in development_rows
    ]
    test_features = [
        vectorize_row(row, numeric_feature_names, categorical_feature_names, numeric_stats)
        for row in test_rows
    ]
    development_binary_targets = [int(row["is_similar"]) for row in development_rows]
    test_binary_targets = [int(row["is_similar"]) for row in test_rows]
    development_similarity_targets = [float(row["similarity_score"]) for row in development_rows]
    test_similarity_targets = [float(row["similarity_score"]) for row in test_rows]
    selected_threshold = float(selected["threshold"])

    linear_model = LinearRegression()
    linear_model.fit(development_features, development_similarity_targets)
    linear_development_predictions = [
        float(prediction) for prediction in linear_model.predict(development_features)
    ]
    linear_test_predictions = [float(prediction) for prediction in linear_model.predict(test_features)]

    logistic_model = LogisticRegression(
        C=1.0 / float(selected["l2_penalty"]),
        max_iter=1000,
        random_state=42,
    )
    logistic_model.fit(development_features, development_binary_targets)
    logistic_development_probabilities = [
        float(probability)
        for probability in logistic_model.predict_proba(development_features)[:, 1]
    ]
    logistic_test_probabilities = [
        float(probability) for probability in logistic_model.predict_proba(test_features)[:, 1]
    ]

    return {
        "configuration": {
            "export_path": str(export_path),
            "selected_feature_set": selected["feature_set_name"],
            "selected_l2_penalty": selected["l2_penalty"],
            "selected_probability_threshold": selected_threshold,
            "selected_use_categories": selected["use_categories"],
            "numeric_features": numeric_feature_names,
            "categorical_features": categorical_feature_names,
        },
        "dataset": {
            "row_count": len(rows),
            "split_counts": {key: len(value) for key, value in split_to_rows.items()},
            "label_balance": {
                "similar": sum(int(row["is_similar"]) for row in rows),
                "dissimilar": sum(1 - int(row["is_similar"]) for row in rows),
            },
        },
        "models": {
            "linear_regression": {
                "metrics": {
                    "development": _with_auroc(
                        evaluate_regression_with_threshold(
                            development_similarity_targets,
                            linear_development_predictions,
                            threshold=selected_threshold,
                        ),
                        development_binary_targets,
                        linear_development_predictions,
                    ),
                    "test": _with_auroc(
                        evaluate_regression_with_threshold(
                            test_similarity_targets,
                            linear_test_predictions,
                            threshold=selected_threshold,
                        ),
                        test_binary_targets,
                        linear_test_predictions,
                    ),
                },
            },
            "logistic_regression": {
                "metrics": {
                    "development": _with_auroc(
                        evaluate_probabilities(
                            development_binary_targets,
                            logistic_development_probabilities,
                            threshold=selected_threshold,
                        ),
                        development_binary_targets,
                        logistic_development_probabilities,
                    ),
                    "test": _with_auroc(
                        evaluate_probabilities(
                            test_binary_targets,
                            logistic_test_probabilities,
                            threshold=selected_threshold,
                        ),
                        test_binary_targets,
                        logistic_test_probabilities,
                    ),
                },
            },
        },
        "auroc_curves": {
            "linear_regression": {
                "development": _curve_points(
                    development_binary_targets, linear_development_predictions
                ),
                "test": _curve_points(test_binary_targets, linear_test_predictions),
            },
            "logistic_regression": {
                "development": _curve_points(
                    development_binary_targets, logistic_development_probabilities
                ),
                "test": _curve_points(test_binary_targets, logistic_test_probabilities),
            },
        },
        "plots": {},
    }


def render_markdown(report: dict[str, object]) -> str:
    lines = [
        "# ChEMBL Baseline Models",
        "",
        f"- Export path: {report['configuration']['export_path']}",
        f"- Selected feature set: {report['configuration']['selected_feature_set']}",
        (
            "- Selected probability threshold: "
            f"{report['configuration']['selected_probability_threshold']}"
        ),
        f"- Rows: {report['dataset']['row_count']}",
        (
            "- Split counts: "
            + ", ".join(
                f"{name}={count}" for name, count in report["dataset"]["split_counts"].items()
            )
        ),
        "",
        "## Linear Regression",
        "",
        "| split | mse | mae | accuracy | precision | recall | f1 | auroc |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for split_name in ("development", "test"):
        metrics = report["models"]["linear_regression"]["metrics"][split_name]
        lines.append(
            f"| {split_name} | {metrics['mse']} | {metrics['mae']} | {metrics['accuracy']} | "
            f"{metrics['precision']} | {metrics['recall']} | {metrics['f1']} | {metrics['auroc']} |"
        )

    lines.extend(
        [
            "",
            "## Logistic Regression",
            "",
            "| split | log_loss | brier | accuracy | precision | recall | f1 | auroc |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for split_name in ("development", "test"):
        metrics = report["models"]["logistic_regression"]["metrics"][split_name]
        lines.append(
            f"| {split_name} | {metrics['log_loss']} | {metrics['brier_score']} | "
            f"{metrics['accuracy']} | {metrics['precision']} | {metrics['recall']} | "
            f"{metrics['f1']} | {metrics['auroc']} |"
        )

    if report.get("plots"):
        lines.extend(
            [
                "",
                "## AUROC Curves",
                "",
                f"![ChEMBL linear regression AUROC]({report['plots']['linear_auroc_curve']})",
                "",
                f"![ChEMBL logistic regression AUROC]({report['plots']['logistic_auroc_curve']})",
            ]
        )
    return "\n".join(lines) + "\n"


def write_report(
    report: dict[str, object], reports_dir: Path = DEFAULT_REPORTS_DIR
) -> tuple[Path, Path]:
    reports_dir.mkdir(parents=True, exist_ok=True)
    report["plots"] = generate_plots(report, reports_dir)
    json_path = reports_dir / "chembl_baseline_models.json"
    markdown_path = reports_dir / "chembl_baseline_models.md"
    json_path.write_text(json.dumps(report, indent=2))
    markdown_path.write_text(render_markdown(report))
    return json_path, markdown_path


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Train and report ChEMBL linear/logistic baseline AUROC curves."
    )
    parser.add_argument(
        "export_path",
        nargs="?",
        default=str(DEFAULT_EXPORT_PATH),
        help=f"Modeling CSV exported from the SQL ETL pipeline (default: {DEFAULT_EXPORT_PATH})",
    )
    parser.add_argument(
        "--reports-dir",
        default=str(DEFAULT_REPORTS_DIR),
        help=f"Directory for JSON/Markdown reports (default: {DEFAULT_REPORTS_DIR})",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    export_path = Path(args.export_path).expanduser().resolve()
    reports_dir = Path(args.reports_dir).expanduser().resolve()
    report = build_report(export_path)
    json_path, markdown_path = write_report(report, reports_dir=reports_dir)
    linear_test = report["models"]["linear_regression"]["metrics"]["test"]
    logistic_test = report["models"]["logistic_regression"]["metrics"]["test"]
    print(f"Wrote {json_path}")
    print(f"Wrote {markdown_path}")
    print(f"Linear test AUROC: {linear_test['auroc']}")
    print(f"Logistic test AUROC: {logistic_test['auroc']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
