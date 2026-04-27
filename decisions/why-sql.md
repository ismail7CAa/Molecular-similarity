# Why SQL

We chose SQL because the project moved beyond a single flat CSV. Once we started handling molecules, activities, targets, and generated pair rows, a relational database became the clearest way to keep the data organized.

SQL helped us:

- Keep molecules, targets, activities, and pair exports as separate concepts.
- Rebuild modeling exports reproducibly instead of manually editing files.
- Query intermediate states when something looked wrong.
- Avoid duplicating raw activity data across many generated files.
- Make the ETL pipeline easier to debug and explain.

The benefit is not only storage. SQL gave the workflow a transparent audit trail: raw ChEMBL-like inputs go in, normalized tables are created, and modeling rows come out through repeatable queries.

