# Ideas For Next Work

## Stronger Models

Compare the current logistic models against:

- Random forest classifiers.
- Gradient boosting classifiers.
- Calibrated classifiers for better probability estimates.
- Target-specific models where enough examples exist.

## Better Validation

Add stronger validation splits:

- Scaffold split by molecule structure.
- Target-held-out split.
- Time-based split if source dates are available.

These would test whether the model generalizes beyond similar molecules and familiar targets.

## More Chemistry Features

Add or evaluate:

- Molecular scaffolds.
- Functional-group counts.
- More fingerprint families.
- Physicochemical descriptor sets.

## Model Interpretation

Add explanations for model behavior:

- Feature importance summaries.
- Coefficient reports grouped by feature family.
- Per-target error analysis.

## Data Pipeline Growth

Extend the ETL pipeline to support larger ChEMBL pulls and configurable target selection. This would make the project easier to reuse for other target families.

