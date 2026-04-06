# Baseline Models

- Decision threshold: 0.5
- Rows: 100
- Feature counts: numeric=60, categorical=3
- Split counts: train=80, val=10, test=10

## Linear Regression

| split | mse | mae | accuracy | precision | recall | f1 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| train | 0.0071 | 0.0657 | 0.95 | 0.9556 | 0.9556 | 0.9556 |
| val | 0.0235 | 0.1391 | 0.7 | 1.0 | 0.5714 | 0.7273 |
| test | 0.0207 | 0.1097 | 0.7 | 0.5 | 0.6667 | 0.5714 |

## Logistic Regression

| split | log_loss | brier | accuracy | precision | recall | f1 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| train | 0.0198 | 0.0019 | 1.0 | 1.0 | 1.0 | 1.0 |
| val | 0.8481 | 0.2633 | 0.6 | 0.8 | 0.5714 | 0.6667 |
| test | 1.1047 | 0.2799 | 0.7 | 0.5 | 1.0 | 0.6667 |

## Test Predictions

| pair_id | target | type | actual | linear | logistic | actual_label |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| 004 | HERG | dis2D,sim3D | 0.75 | 0.729 | 0.9365 | 1 |
| 014 | 5HT2B | dis2D,sim3D | 0.4545 | 0.4764 | 0.8643 | 0 |
| 015 | 5HT2B | dis2D,sim3D | 0.65 | 0.3439 | 0.6786 | 1 |
| 018 | HERG | dis2D,sim3D | 0.4483 | 0.4684 | 0.1695 | 0 |
| 029 | CYP2D6 | sim2D,dis3D | 0.4783 | 0.6097 | 0.9938 | 0 |
| 032 | CYP2D6 | sim2D,dis3D | 0.381 | 0.5873 | 0.9623 | 0 |
| 036 | CYP2D6 | sim2D,dis3D | 0.6471 | 0.5341 | 0.9579 | 1 |
| 082 | 5HT2B | dis2D,dis3D | 0.1875 | 0.2422 | 0.0015 | 0 |
| 087 | 5HT2B | dis2D,dis3D | 0.0 | 0.0355 | 0.0 | 0 |
| 095 | HERG | dis2D,dis3D | 0.0 | 0.1871 | 0.0006 | 0 |
