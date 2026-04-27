from __future__ import annotations

import math


def roc_curve_points(
    targets: list[int],
    scores: list[float],
) -> list[dict[str, float]]:
    if len(targets) != len(scores):
        raise ValueError("targets and scores must have the same length")

    finite_pairs = [
        (int(target), float(score))
        for target, score in zip(targets, scores, strict=True)
        if math.isfinite(float(score))
    ]
    positive_count = sum(1 for target, _ in finite_pairs if target == 1)
    negative_count = len(finite_pairs) - positive_count
    if positive_count == 0 or negative_count == 0:
        return []

    thresholds = [float("inf")]
    thresholds.extend(sorted({score for _, score in finite_pairs}, reverse=True))
    thresholds.append(float("-inf"))

    points: list[dict[str, float]] = []
    for threshold in thresholds:
        true_positive = 0
        false_positive = 0
        for target, score in finite_pairs:
            if score >= threshold:
                if target == 1:
                    true_positive += 1
                else:
                    false_positive += 1
        points.append(
            {
                "threshold": threshold,
                "false_positive_rate": false_positive / negative_count,
                "true_positive_rate": true_positive / positive_count,
            }
        )

    return points


def auroc_score(targets: list[int], scores: list[float]) -> float | None:
    points = roc_curve_points(targets, scores)
    if not points:
        return None

    area = 0.0
    for left, right in zip(points, points[1:]):
        width = right["false_positive_rate"] - left["false_positive_rate"]
        height = (left["true_positive_rate"] + right["true_positive_rate"]) / 2.0
        area += width * height

    return round(area, 4)

