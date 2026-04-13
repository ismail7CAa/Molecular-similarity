# Threshold-Based Similarity Model

- Similarity label threshold: 0.5
- Selected probability threshold: 0.55
- Selected feature set: core_similarity
- Selected L2 penalty: 0.1
- Rows: 100
- Feature counts: numeric=3, categorical=3
- Split counts: train=80, val=10, test=10

## Model Selection

- Cross-validation summary: folds=5, mean_f1=0.8987, mean_accuracy=0.8775, mean_log_loss=0.3704

## Classification Metrics

| split | log_loss | brier | accuracy | precision | recall | f1 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| development | 0.3664 | 0.1072 | 0.8778 | 0.8596 | 0.9423 | 0.8991 |
| test | 0.6272 | 0.2228 | 0.6 | 0.4286 | 1.0 | 0.6 |

## Test Predictions

| pair_id | target | type | frac_similar | actual_label | probability | predicted_label |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| 004 | HERG | dis2D,sim3D | 0.75 | 1 | 0.585 | 1 |
| 014 | 5HT2B | dis2D,sim3D | 0.4545 | 0 | 0.5671 | 1 |
| 015 | 5HT2B | dis2D,sim3D | 0.65 | 1 | 0.6402 | 1 |
| 018 | HERG | dis2D,sim3D | 0.4483 | 0 | 0.5569 | 1 |
| 029 | CYP2D6 | sim2D,dis3D | 0.4783 | 0 | 0.7521 | 1 |
| 032 | CYP2D6 | sim2D,dis3D | 0.381 | 0 | 0.7117 | 1 |
| 036 | CYP2D6 | sim2D,dis3D | 0.6471 | 1 | 0.6526 | 1 |
| 082 | 5HT2B | dis2D,dis3D | 0.1875 | 0 | 0.2346 | 0 |
| 087 | 5HT2B | dis2D,dis3D | 0.0 | 0 | 0.0798 | 0 |
| 095 | HERG | dis2D,dis3D | 0.0 | 0 | 0.2 | 0 |
