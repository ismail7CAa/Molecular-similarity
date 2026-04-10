# Threshold-Based Similarity Model

- Similarity label threshold: 0.5
- Selected probability threshold: 0.55
- Selected feature set: core_similarity
- Selected L2 penalty: 0.01
- Rows: 100
- Feature counts: numeric=3, categorical=3
- Split counts: train=80, val=10, test=10

## Model Selection

- Cross-validation summary: folds=5, mean_f1=0.9146, mean_accuracy=0.8991, mean_log_loss=0.2851

## Classification Metrics

| split | log_loss | brier | accuracy | precision | recall | f1 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| development | 0.2665 | 0.0827 | 0.9111 | 0.8929 | 0.9615 | 0.9259 |
| test | 0.6682 | 0.2373 | 0.7 | 0.5 | 1.0 | 0.6667 |

## Test Predictions

| pair_id | target | type | frac_similar | actual_label | probability | predicted_label |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| 004 | HERG | dis2D,sim3D | 0.75 | 1 | 0.643 | 1 |
| 014 | 5HT2B | dis2D,sim3D | 0.4545 | 0 | 0.5236 | 0 |
| 015 | 5HT2B | dis2D,sim3D | 0.65 | 1 | 0.6842 | 1 |
| 018 | HERG | dis2D,sim3D | 0.4483 | 0 | 0.5922 | 1 |
| 029 | CYP2D6 | sim2D,dis3D | 0.4783 | 0 | 0.8753 | 1 |
| 032 | CYP2D6 | sim2D,dis3D | 0.381 | 0 | 0.8193 | 1 |
| 036 | CYP2D6 | sim2D,dis3D | 0.6471 | 1 | 0.7186 | 1 |
| 082 | 5HT2B | dis2D,dis3D | 0.1875 | 0 | 0.0478 | 0 |
| 087 | 5HT2B | dis2D,dis3D | 0.0 | 0 | 0.004 | 0 |
| 095 | HERG | dis2D,dis3D | 0.0 | 0 | 0.0452 | 0 |
