# Molecular-similarity

Initial repository scaffold for the Molecular-similarity project.

## Local Environment

1. Create the virtual environment:
   `python3 -m venv .venv`
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
6. Open the generated report files in `exploration/reports/`

## CI/CD

This repository includes a starter GitHub Actions pipeline in
`.github/workflows/ci-cd.yml`.

- CI runs on pushes and pull requests.
- CD builds and uploads distribution artifacts on version tags like `v0.1.0`.
- The workflow is intentionally defensive while the project is still being
  scaffolded, so it skips dependency installation and tests when the relevant
  files do not exist yet.
