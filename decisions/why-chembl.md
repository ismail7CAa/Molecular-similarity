# Why ChEMBL

We chose ChEMBL because the first prepared dataset was useful for prototyping, but too small for reliable model evaluation. Metrics such as AUROC need enough positive and negative examples in the held-out split to produce a meaningful curve.

ChEMBL gave the project:

- More molecule pairs across multiple biological targets.
- A larger held-out test split for less noisy evaluation.
- Real assay context through targets, activity values, and standard types.
- A better base for comparing linear and logistic baselines.

The main tradeoff is complexity. ChEMBL data needs cleaning, normalization, target filtering, and careful pair construction before it becomes modeling-ready. That extra work is why the ETL and SQL layers became important parts of the project.

