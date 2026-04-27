# Project Challenges

## Data Size And Evaluation

The first dataset was useful for validating scripts, but too small for confident model comparison. It helped prove the workflow, but ChEMBL was needed for stronger evaluation.

## Data Modeling

Moving from raw activity rows to molecule pairs required careful choices:

- How to define similar and dissimilar pairs.
- How to preserve target context.
- How to avoid mixing raw activity values with generated model labels.

## Feature Engineering

The project needed features that worked without relying on unavailable 3D conformers. RDKit fingerprints, SMILES-derived features, and target context gave a practical structure-aware feature set.

## Reproducibility

The project includes generated reports and images. Keeping those outputs in sync with code changes became a recurring task, especially when metrics or plot styles changed.

## Evaluation Communication

Some metrics are technically correct but visually confusing on small data. The AUROC work made this clear: the final result needed to use ChEMBL, not the tiny starter split.

