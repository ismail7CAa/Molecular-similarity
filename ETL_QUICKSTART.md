# SQL ETL Pipeline - Quick Start

## Overview
The ETL pipeline transforms raw ChEMBL data into a structured SQL database optimized for molecular similarity modeling.

**Flow**: Extract (PDB/SDF) → Transform (parse/normalize) → Load (Database)

## Quick Commands

### 1. Setup Database & Schema
```bash
source .venv/bin/activate
python scripts/etl_pipeline.py --db ./data/chembl.db --create-schema
```

### 2. Build Dataset Index (if not done)
```bash
python scripts/build_dataset_index.py ./data/chembl
```

### 3. Load Data into Database
```bash
python scripts/etl_pipeline.py --db ./data/chembl.db --load --index ./exploration/reports/dataset_index.json
```

### 4. Check Pipeline Stats
```bash
python scripts/etl_pipeline.py --db ./data/chembl.db --stats
```

### 5. Export for Modeling
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
- Optional: for enriching molecular features

## Pipeline Workflow

```
1. Raw ChEMBL files (PDB, SVG)
    ↓
2. build_dataset_index.py → dataset_index.json
    ↓
3. etl_pipeline.py (Extract, Transform)
    ↓
4. SQL Database (molecule_pairs table)
    ↓
5. Export CSV → ML Pipeline
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
