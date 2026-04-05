# Dataset Index

- Dataset root: `/Users/ismailcherkaouiaadil/Downloads/dataset_Similarity_Prediction/original_training_set`
- Pair rows: 100

## Columns

- `pair_id`: shared pair identifier
- `pdb_path_a` / `pdb_path_b`: 3D conformer paths
- `svg_path_a` / `svg_path_b`: 2D image paths
- `compound_name_a` / `compound_name_b`: names extracted from PDB `COMPND` records
- `atom_count_*` and `heavy_atom_count_*`: per-variant structural size
- `*_delta`: simple `b - a` difference for pair comparison

## Preview

| pair_id | atoms_a | atoms_b | heavy_a | heavy_b | delta_atoms | complete |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| 001 | 40 | 47 | 17 | 20 | 7 | True |
| 002 | 59 | 58 | 31 | 30 | -1 | True |
| 003 | 28 | 47 | 14 | 21 | 19 | True |
| 004 | 57 | 30 | 28 | 19 | -27 | True |
| 005 | 24 | 27 | 10 | 11 | 3 | True |
| 006 | 43 | 24 | 21 | 17 | -19 | True |
| 007 | 28 | 31 | 17 | 20 | 3 | True |
| 008 | 58 | 28 | 26 | 20 | -30 | True |
| 009 | 45 | 42 | 19 | 19 | -3 | True |
| 010 | 51 | 48 | 25 | 24 | -3 | True |
