# Molecular-similarity

End-to-End molecular similarity project focused on reproducible data exploration, ETL, and baseline modeling workflows.

## Project Status

This project is still under active development and deployment. The ETL, modeling, and CLI workflows are already usable for experimentation, but the overall system should not yet be treated as a finalized production deployment.

## Local Environment

1. Create the virtual environment:
   `python3.11 -m venv .venv`
2. Activate it:
   `source .venv/bin/activate`
3. Install the project with development dependencies:
   `pip install -e .[dev]`
4. Copy the environment template if needed:
   `cp .env.example .env`

## Data Exploration

Use the exploration workspace to describe and inspect datasets before modeling.

1. Activate the environment:
   `source .venv/bin/activate`
2. Generate the dataset summary:
   `python scripts/explore_dataset.py "/path/to/dataset"`
3. Build the pair-level dataset index:
   `python scripts/build_dataset_index.py "/path/to/dataset"`
4. Prepare reproducible train/val/test splits:
   `python scripts/prepare_dataset.py "/path/to/dataset"`
5. Run the baseline experiment suite with richer features:
   `python scripts/run_linear_regression_baseline.py`
6. Train a threshold-based classifier for similar vs not similar pairs:
   `python scripts/run_similarity_threshold_model.py`
7. Export SQL-derived activity pairs for modeling:
   `python scripts/etl_pipeline.py --db ./data/chembl.db --export ./data/chembl_modeling.csv`
8. Train the SQL-backed activity-pair model:
   `python scripts/run_sql_activity_pair_model.py ./data/chembl_modeling.csv`
9. Open the generated report files in `exploration/reports/`

## Reproducibility

This project aims to keep the modeling path reproducible and scriptable.

- Prefer Python `3.11` for the supported RDKit workflow.
- The SQL activity-pair model is implemented as reusable package code in `src/molecular_similarity/sql_activity_model.py`.
- The threshold classifier is implemented as reusable package code in `src/molecular_similarity/threshold_model.py`.
- The linear/logistic baseline is implemented as reusable package code in `src/molecular_similarity/linear_regression_baseline.py`.
- You can run the same model through either:
  `python scripts/run_sql_activity_pair_model.py ./data/chembl_modeling.csv`
  or
  `molecular-similarity-sql-activity-model ./data/chembl_modeling.csv`
- You can run the baseline suite through either:
  `python scripts/run_linear_regression_baseline.py`
  or
  `molecular-similarity-linear-baseline`
- You can run the threshold classifier through either:
  `python scripts/run_similarity_threshold_model.py`
  or
  `molecular-similarity-threshold-model`
- Tests cover ETL, report generation, and the basic CLI surface with `pytest`.

## Precision Visualization

The strongest current model presentation is the SQL-backed activity-pair report in `exploration/reports/sql_activity_pair_model.md`.

- It includes held-out overall metrics and per-target metrics for `Cytochrome P450 2D6`, `5-hydroxytryptamine receptor 2B`, and `KCNH2`.
- It also generates precision-first figures that highlight where the model is strongest on unseen data.
- The current best emphasis is precision rather than recall, so the report is designed to make that tradeoff visible target by target.

## Docker

You can run the packaged SQL precision report inside Docker:

1. Build the image:
   `docker build -t molecular-similarity .`
2. Run the default SQL report workflow:
   `docker run --rm -v "$(pwd)/exploration/reports:/app/exploration/reports" molecular-similarity`

The default container command runs:
`molecular-similarity-sql-activity-model ./data/chembl_modeling.csv --reports-dir ./exploration/reports`

## CI/CD

This repository includes a starter GitHub Actions pipeline in
`.github/workflows/ci-cd.yml`.

- CI runs on pushes and pull requests.
- CD builds and uploads distribution artifacts on version tags like `v0.1.0`.
- The workflow is intentionally defensive while the project is still being
  scaffolded, so it skips dependency installation and tests when the relevant
  files do not exist yet.
