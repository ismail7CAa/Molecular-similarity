# Why These Models

We used simple models first because the project needed a clear baseline before adding complexity.

The linear regression baseline predicts the continuous similarity score. It is easy to inspect and gives a direct sense of whether the engineered features contain a useful signal.

The logistic regression baseline predicts the binary similar/dissimilar label. It is a strong first classifier because it produces probabilities, supports AUROC evaluation, and is still interpretable through feature weights.

The threshold model helped test whether a tuned decision threshold could improve classification behavior on the smaller prepared dataset.

The SQL activity-pair logistic model became the main ChEMBL workflow because it used richer RDKit and structure-derived features from a larger export.

We did not jump immediately to more complex models because simple baselines make failures easier to understand. Once the data pipeline and metrics are stable, tree-based models or neural approaches can be compared fairly.

