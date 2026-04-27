# Why AUROC

We added AUROC because accuracy, precision, recall, and F1 all depend on a chosen classification threshold. AUROC evaluates how well model scores rank similar pairs above dissimilar pairs across many thresholds.

The first prepared dataset was too small for a useful-looking AUROC curve. The curve had only a few steps because the test split had few examples and few distinct score values.

The ChEMBL export gives a better AUROC view because the test split is larger. That is why the final AUROC figures are based on ChEMBL linear and logistic baselines instead of the first small dataset.

AUROC is useful here because:

- It compares ranking quality without locking into one threshold.
- It lets linear scores and logistic probabilities be compared on the same idea.
- It reveals whether the model separates classes even when a chosen threshold is imperfect.

