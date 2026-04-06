# Linear Regression Baseline

- Decision threshold: 0.5
- Rows: 100
- Split counts: train=80, val=10, test=10

## Metrics

| split | mse | mae | accuracy | precision | recall | f1 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| train | 0.0156 | 0.1008 | 0.825 | 0.8444 | 0.8444 | 0.8444 |
| val | 0.0084 | 0.0789 | 0.9 | 1.0 | 0.8571 | 0.9231 |
| test | 0.0179 | 0.1174 | 0.6 | 0.4 | 0.6667 | 0.5 |

## Test Predictions

| pair_id | target | type | actual | predicted | actual_label | predicted_label |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| 004 | HERG | dis2D,sim3D | 0.75 | 0.5888 | 1 | 1 |
| 014 | 5HT2B | dis2D,sim3D | 0.4545 | 0.4655 | 0 | 0 |
| 015 | 5HT2B | dis2D,sim3D | 0.65 | 0.4893 | 1 | 0 |
| 018 | HERG | dis2D,sim3D | 0.4483 | 0.509 | 0 | 1 |
| 029 | CYP2D6 | sim2D,dis3D | 0.4783 | 0.6271 | 0 | 1 |
| 032 | CYP2D6 | sim2D,dis3D | 0.381 | 0.611 | 0 | 1 |
| 036 | CYP2D6 | sim2D,dis3D | 0.6471 | 0.5421 | 1 | 1 |
| 082 | 5HT2B | dis2D,dis3D | 0.1875 | 0.0772 | 0 | 0 |
| 087 | 5HT2B | dis2D,dis3D | 0.0 | 0.0318 | 0 | 0 |
| 095 | HERG | dis2D,dis3D | 0.0 | 0.1543 | 0 | 0 |
