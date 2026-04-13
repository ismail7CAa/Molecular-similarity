# SQL ETL Pipeline - Quick Start

## Overview
The ETL pipeline supports two import paths into a structured SQL database:

1. Pair-file ETL for local `conformers_3D/` and `images_2D/` datasets
2. Direct import from the official ChEMBL SQLite release

**Flows**
- Pair files: Extract (PDB/SVG) → Transform (parse/normalize) → Load (Database)
- Official DB: Extract (ChEMBL SQLite) → Transform (select/join) → Load (Database)

## Quick Commands

### 1. Setup Database & Schema
```bash
source .venv/bin/activate
python scripts/etl_pipeline.py --db ./data/chembl.db --create-schema
```

### 2. Import Official ChEMBL SQLite
```bash
python scripts/etl_pipeline.py \
  --db ./data/chembl.db \
  --create-schema \
  --import-chembl-sqlite \
  --chembl-sqlite ./data/chembl/raw/chembl_36_sqlite/chembl_36/chembl_36_sqlite/chembl_36.db \
  --limit 10000
```

To also import activities for the imported molecules:
```bash
python scripts/etl_pipeline.py \
  --db ./data/chembl.db \
  --import-chembl-sqlite \
  --chembl-sqlite ./data/chembl/raw/chembl_36_sqlite/chembl_36/chembl_36_sqlite/chembl_36.db \
  --limit 10000 \
  --include-activities \
  --activity-limit 50000
```

### 3. Build Dataset Index (if using pair files)
```bash
python scripts/build_dataset_index.py ./data/chembl
```

### 4. Load Pair Data into Database
```bash
python scripts/etl_pipeline.py --db ./data/chembl.db --load --index ./exploration/reports/dataset_index.json
```

### 5. Check Pipeline Stats
```bash
python scripts/etl_pipeline.py --db ./data/chembl.db --stats
```

### 6. Export Pair Data for Modeling
```bash
python scripts/etl_pipeline.py --db ./data/chembl.db --export ./data/chembl_modeling.csv
```

## Database Schema

### Tables

#### `molecules`
- Core molecule records
- Stores: ChEMBL ID, SMILES, InChI, molecular properties

#### `conformers`
- 3D structure information
- Links to molecule via `molecule_id`
- Stores: atom counts, element composition

#### `images`
- 2D structure images (SVG/PNG)
- Links to molecule via `molecule_id`

#### `molecule_pairs`
- **Main table for similarity prediction**
- Stores molecule A-B pairs with flags for data completeness
- Ready for training/testing models

#### `activities`
- Bioactivity data from ChEMBL
- Stores activity type, standard type, value, units, and target annotations
- Useful for enriching molecular features directly from the official ChEMBL DB

## Pipeline Workflow

```
Option A: pair files
1. Raw ChEMBL files (PDB, SVG)
    ↓
2. build_dataset_index.py → dataset_index.json
    ↓
3. etl_pipeline.py --load
    ↓
4. SQL database (`molecule_pairs`)
    ↓
5. Export CSV → ML pipeline

Option B: official ChEMBL DB
1. `chembl_36.db`
    ↓
2. etl_pipeline.py --import-chembl-sqlite
    ↓
3. SQL database (`molecules`, `activities`)
    ↓
4. Downstream analysis / feature engineering
```

## Next: Build ML Model

Once data is in the database:
```bash
python scripts/run_linear_regression_baseline.py
python scripts/run_similarity_threshold_model.py
```

## Customization

Edit `etl_pipeline.py` to:
- Add custom transformations in `load_from_index()`
- Add new tables for additional features
- Connect to PostgreSQL (change `db_type`)

---

**Database Path**: `./data/chembl.db`
**Schema File**: `./sql/schema.sql`
