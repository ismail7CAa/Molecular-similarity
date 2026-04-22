# Molecular-similarity

I built this project as an end-to-end molecular similarity workflow. I started with raw pair-level molecule data, added an ETL pipeline for structured ChEMBL imports, trained several baseline models, and then pushed the project toward a more reproducible SQL-backed workflow with package CLIs, tests, reports, and Docker support.

The project is still under active development and deployment. I can run the data exploration, ETL, feature engineering, training, evaluation, and report generation locally, but I do not present it as a finished production system yet.

## What I Built

I used this repository to cover the whole path from raw data to model evaluation:

- I explored the original dataset and generated dataset summaries, pair indexes, and reproducible train/validation/test splits.
- I built an ETL pipeline that imports a compact ChEMBL subset into SQLite, generates activity-derived molecule pairs, and exports a modeling-ready CSV.
- I built three modeling paths:
  - a linear/logistic baseline
  - a threshold-based similarity classifier for the small prepared dataset
  - a SQL-backed activity-pair model, which is the strongest current workflow
- I packaged the model code under `src/molecular_similarity/` and kept `scripts/` as thin wrappers so the same workflows can be run from Python scripts or installed CLIs.
- I added tests, Markdown/JSON reports, and precision-focused visual outputs so the results are easy to inspect.

## How The Pipeline Works

I used the following project flow:

1. I explored the input data with:
   `scripts/explore_dataset.py`
   `scripts/build_dataset_index.py`
   `scripts/prepare_dataset.py`
2. I used the ETL pipeline in:
   `scripts/etl_pipeline.py`
   to import compact ChEMBL data into `data/chembl.db`, generate activity-based pairs, and export `data/chembl_modeling.csv`.
3. I trained baseline and threshold models for smaller pair-level experiments.
4. I trained the main SQL-backed activity-pair model from:
   `src/molecular_similarity/sql_activity_model.py`
5. I evaluated the model on held-out unseen data and generated:
   - JSON reports
   - Markdown reports
   - precision-first plots

I also added a figure generator in:
`scripts/generate_pipeline_figure.py`

Running it writes:
`exploration/reports/project_pipeline.png`

The figure shows the exact pipeline from raw inputs to ETL, SQL storage, model training, precision evaluation, and reproducibility tooling.

## Main Results

The strongest current result is the SQL-backed activity-pair model trained on the exported ChEMBL-based dataset.

Held-out SQL test metrics:

- accuracy: `0.7313`
- precision: `0.6243`
- recall: `0.5567`
- F1: `0.5885`
- log loss: `0.5301`

Precision is the priority in this project, so I focused the report on where the model is strongest by target.

Per-target held-out precision:

- `Cytochrome P450 2D6`: precision `0.6783`, recall `0.6382`, F1 `0.6576`
- `5-hydroxytryptamine receptor 2B`: precision `0.5896`, recall `0.5643`, F1 `0.5766`
- `Voltage-gated inwardly rectifying potassium channel KCNH2`: precision `0.5844`, recall `0.4286`, F1 `0.4945`

The strongest precision result is currently `Cytochrome P450 2D6`.

I also kept the earlier smaller-dataset experiments:

- threshold model test accuracy: `0.7`
- threshold model test precision: `0.5`
- baseline logistic test accuracy: `0.7`
- baseline logistic test precision: `0.5`

Those smaller experiments were useful for debugging and validating the workflow, but the SQL-backed model is the one I use as the main project result.

## Reports And Visual Outputs

I generated the main SQL report here:

- `exploration/reports/sql_activity_pair_model.json`
- `exploration/reports/sql_activity_pair_model.md`

I generated precision-first visual outputs here:

- `exploration/reports/sql_activity_pair_precision_by_target.png`
- `exploration/reports/sql_activity_pair_precision_recall.png`

I also generated the full project pipeline figure here:

- `exploration/reports/project_pipeline.png`

## Reproducibility

I wanted the project to be runnable the same way every time, so I used:

- Python `3.11`
- package modules under `src/molecular_similarity/`
- thin CLI wrappers under `scripts/`
- `pytest` for tests
- `ruff` for linting

I can run the main workflows either from the scripts or from the installed CLIs:

- `python scripts/run_linear_regression_baseline.py`
- `molecular-similarity-linear-baseline`
- `python scripts/run_similarity_threshold_model.py`
- `molecular-similarity-threshold-model`
- `python scripts/run_sql_activity_pair_model.py ./data/chembl_modeling.csv`
- `molecular-similarity-sql-activity-model ./data/chembl_modeling.csv`

## Local Setup

1. Create the virtual environment:
   `python3.11 -m venv .venv`
2. Activate it:
   `source .venv/bin/activate`
3. Install the project with development dependencies:
   `pip install -e .[dev]`
4. Generate the pipeline figure:
   `python scripts/generate_pipeline_figure.py`

## Main Commands I Used

Data exploration:

- `python scripts/explore_dataset.py "/path/to/dataset"`
- `python scripts/build_dataset_index.py "/path/to/dataset"`
- `python scripts/prepare_dataset.py "/path/to/dataset"`

ETL and SQL export:

- `python scripts/etl_pipeline.py --db ./data/chembl.db --export ./data/chembl_modeling.csv`

Model training:

- `python scripts/run_linear_regression_baseline.py`
- `python scripts/run_similarity_threshold_model.py`
- `python scripts/run_sql_activity_pair_model.py ./data/chembl_modeling.csv`

Precision pipeline figure:

- `python scripts/generate_pipeline_figure.py`

Verification:

- `python -m ruff check .`
- `python -m pytest -q`

## Docker

I added a Docker workflow for a fast, reliable container run.

Build:
`docker build -t molecular-similarity .`

Run the default smoke workflow:
`docker run --rm -v "$(pwd)/exploration/reports:/app/exploration/reports" molecular-similarity`

The default container command generates:
`exploration/reports/project_pipeline.png`

If I want to run the heavier SQL precision workflow inside Docker, I use an explicit command:

`docker run --rm -v "$(pwd)/exploration/reports:/app/exploration/reports" molecular-similarity molecular-similarity-sql-activity-model ./data/chembl_modeling.csv --reports-dir ./exploration/reports`

I changed the default container command to the lighter pipeline-figure workflow because it finishes quickly and is better as a Docker smoke test. The SQL report still works as an optional container command, but it is heavier and slower.

## Project Status

I consider the ETL, model training, reporting, and reproducibility layers to be in a good research-project state.

What is already solid:

- SQL ETL pipeline
- reproducible model CLIs
- basic tests
- held-out evaluation
- precision-focused reporting

What is still not final:

- Docker runtime verification on this machine
- stronger production deployment
- more model improvement for higher precision on every target, especially `KCNH2`

## CI/CD

I also kept a starter GitHub Actions workflow in:
`.github/workflows/ci-cd.yml`

It runs CI on pushes and pull requests, and it can build distribution artifacts on tagged releases.
