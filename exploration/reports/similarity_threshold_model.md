# Threshold-Based Similarity Model

- Decision threshold: 0.5
- Rows: 100
- Feature counts: numeric=60, categorical=3
- Split counts: train=80, val=10, test=10

## Classification Metrics

| split | log_loss | brier | accuracy | precision | recall | f1 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| train | 0.0198 | 0.0019 | 1.0 | 1.0 | 1.0 | 1.0 |
| val | 0.8481 | 0.2633 | 0.6 | 0.8 | 0.5714 | 0.6667 |
| test | 1.1047 | 0.2799 | 0.7 | 0.5 | 1.0 | 0.6667 |

## Test Predictions

| pair_id | target | type | frac_similar | actual_label | probability | predicted_label |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| 004 | HERG | dis2D,sim3D | 0.75 | 1 | 0.9365 | 1 |
| 014 | 5HT2B | dis2D,sim3D | 0.4545 | 0 | 0.8643 | 1 |
| 015 | 5HT2B | dis2D,sim3D | 0.65 | 1 | 0.6786 | 1 |
| 018 | HERG | dis2D,sim3D | 0.4483 | 0 | 0.1695 | 0 |
| 029 | CYP2D6 | sim2D,dis3D | 0.4783 | 0 | 0.9938 | 1 |
| 032 | CYP2D6 | sim2D,dis3D | 0.381 | 0 | 0.9623 | 1 |
| 036 | CYP2D6 | sim2D,dis3D | 0.6471 | 1 | 0.9579 | 1 |
| 082 | 5HT2B | dis2D,dis3D | 0.1875 | 0 | 0.0015 | 0 |
| 087 | 5HT2B | dis2D,dis3D | 0.0 | 0 | 0.0 | 0 |
| 095 | HERG | dis2D,dis3D | 0.0 | 0 | 0.0006 | 0 |
