# Why ETL Instead Of ELT

We chose ETL because the data needed validation and normalization before it was useful for modeling.

In an ELT workflow, raw data is loaded first and transformed later inside the storage system. That can be powerful for large warehouses, but here the project needed controlled preprocessing before generating molecule-pair rows.

ETL was better because we needed to:

- Validate activity fields before loading them into SQLite tables.
- Normalize target, molecule, and activity records into a clean schema.
- Generate pair rows from known-clean records.
- Export a modeling CSV with consistent labels and split assignments.
- Catch data problems early, close to the source.

The main benefit is confidence. By transforming before and during load, the database starts in a cleaner state, and downstream model scripts can rely on a stable structure.

