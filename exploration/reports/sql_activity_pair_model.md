# SQL Activity Pair Model

- Export path: data/chembl_modeling.csv
- Selected feature set: structure_enriched
- Selected probability threshold: 0.45
- Selected L2 penalty: 0.01
- Rows: 12015
- Split counts: train=9618, val=1247, test=1150
- Label balance: similar=4184, dissimilar=7831
- Precision-focused highlight: Cytochrome P450 2D6 has the strongest test precision at 0.6783

## Validation Selection

- Validation metrics: accuracy=0.7418, f1=0.5995, log_loss=0.5118

## Classification Metrics

| split | log_loss | brier | accuracy | precision | recall | f1 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| development | 0.5221 | 0.1736 | 0.7449 | 0.6554 | 0.5651 | 0.6069 |
| test | 0.5301 | 0.1767 | 0.7313 | 0.6243 | 0.5567 | 0.5885 |

## Per-Target Test Metrics

| target | samples | similar | dissimilar | log_loss | brier | accuracy | precision | recall | f1 | tp | tn | fp | fn |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 5-hydroxytryptamine receptor 2B | 376 | 140 | 236 | 0.5706 | 0.195 | 0.6915 | 0.5896 | 0.5643 | 0.5766 | 79 | 181 | 55 | 61 |
| Cytochrome P450 2D6 | 399 | 152 | 247 | 0.5396 | 0.178 | 0.7469 | 0.6783 | 0.6382 | 0.6576 | 97 | 201 | 46 | 55 |
| Voltage-gated inwardly rectifying potassium channel KCNH2 | 375 | 105 | 270 | 0.4794 | 0.1571 | 0.7547 | 0.5844 | 0.4286 | 0.4945 | 45 | 238 | 32 | 60 |

## Precision View

- Best precision target: Cytochrome P450 2D6 (precision=0.6783, recall=0.6382)
- Lowest recall target: Voltage-gated inwardly rectifying potassium channel KCNH2 (precision=0.5844, recall=0.4286)

## Plots

![Precision by target](sql_activity_pair_precision_by_target.png)

![Precision recall profile](sql_activity_pair_precision_recall.png)

## Test Predictions

| pair_id | target | type | similarity_score | activity_delta | actual_label | probability | predicted_label |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| ACT_CHEMBL1833_EC50_178252_362073 | 5-hydroxytryptamine receptor 2B | EC50 | 0.7686 | 0.301 | 1 | 0.6583 | 1 |
| ACT_CHEMBL1833_EC50_178252_179329 | 5-hydroxytryptamine receptor 2B | EC50 | 0.5 | 1.0 | 1 | 0.4804 | 1 |
| ACT_CHEMBL1833_EC50_178252_415029 | 5-hydroxytryptamine receptor 2B | EC50 | 0.379 | 1.6383 | 0 | 0.5373 | 1 |
| ACT_CHEMBL1833_EC50_178252_202656 | 5-hydroxytryptamine receptor 2B | EC50 | 0.3548 | 1.8182 | 0 | 0.4306 | 0 |
| ACT_CHEMBL1833_EC50_178252_210215 | 5-hydroxytryptamine receptor 2B | EC50 | 0.3545 | 1.821 | 0 | 0.4967 | 1 |
| ACT_CHEMBL1833_EC50_178252_178366 | 5-hydroxytryptamine receptor 2B | EC50 | 0.3218 | 2.1079 | 0 | 0.8024 | 1 |
| ACT_CHEMBL1833_EC50_178252_201062 | 5-hydroxytryptamine receptor 2B | EC50 | 0.2988 | 2.3468 | 0 | 0.4321 | 0 |
| ACT_CHEMBL1833_EC50_80731_178252 | 5-hydroxytryptamine receptor 2B | EC50 | 0.285 | 2.5086 | 0 | 0.3339 | 0 |
| ACT_CHEMBL1833_EC50_178252_202458 | 5-hydroxytryptamine receptor 2B | EC50 | 0.2703 | 2.699 | 0 | 0.2886 | 0 |
| ACT_CHEMBL1833_EC50_76781_178252 | 5-hydroxytryptamine receptor 2B | EC50 | 0.229 | 3.3665 | 0 | 0.1771 | 0 |
| ACT_CHEMBL1833_EC50_178566_197646 | 5-hydroxytryptamine receptor 2B | EC50 | 0.5186 | 0.9281 | 1 | 0.6044 | 1 |
| ACT_CHEMBL1833_EC50_178566_361742 | 5-hydroxytryptamine receptor 2B | EC50 | 0.4744 | 1.1079 | 0 | 0.7065 | 1 |
| ACT_CHEMBL1833_EC50_178124_178566 | 5-hydroxytryptamine receptor 2B | EC50 | 0.4132 | 1.4202 | 0 | 0.6571 | 1 |
| ACT_CHEMBL1833_EC50_178313_178566 | 5-hydroxytryptamine receptor 2B | EC50 | 0.3675 | 1.7212 | 0 | 0.6617 | 1 |
| ACT_CHEMBL1833_EC50_178566_180815 | 5-hydroxytryptamine receptor 2B | EC50 | 0.3333 | 2.0 | 0 | 0.5579 | 1 |
| ACT_CHEMBL1833_EC50_178566_202324 | 5-hydroxytryptamine receptor 2B | EC50 | 0.3288 | 2.041 | 0 | 0.5987 | 1 |
| ACT_CHEMBL1833_EC50_178566_209714 | 5-hydroxytryptamine receptor 2B | EC50 | 0.3138 | 2.1871 | 0 | 0.5865 | 1 |
| ACT_CHEMBL1833_EC50_178566_210802 | 5-hydroxytryptamine receptor 2B | EC50 | 0.3118 | 2.2076 | 0 | 0.4966 | 1 |
| ACT_CHEMBL1833_EC50_179244_360479 | 5-hydroxytryptamine receptor 2B | EC50 | 0.7686 | 0.301 | 1 | 0.5225 | 1 |
| ACT_CHEMBL1833_EC50_179244_180668 | 5-hydroxytryptamine receptor 2B | EC50 | 0.5 | 1.0 | 1 | 0.3103 | 0 |
