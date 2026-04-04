# Data Exploration Workspace

This folder is the starting point for understanding the dataset before we build
features or models.

## Purpose

- describe the dataset structure
- validate file pairing and completeness
- inspect simple molecular metadata from the 3D conformers
- keep generated reports in one predictable place

## Workflow

1. Activate the virtual environment:
   `source .venv/bin/activate`
2. Run the dataset explorer:
   `python scripts/explore_dataset.py "/path/to/dataset"`
3. Review the generated files in `exploration/reports/`

## Generated Files

- `dataset_summary.md`: human-readable overview
- `dataset_summary.json`: structured summary for downstream scripts
- `dataset_overview.html`: quick visual snapshot in the browser

## Current Dataset

The first run was generated from:

`/Users/ismailcherkaouiaadil/Downloads/dataset_Similarity_Prediction/original_training_set`
