---
model: model-a
registry: wandb-registry-model/model-a
version: v1
run: tdvvc98x (random-forest-run)
commit: 18f5042
---

# Model A: probability of default

## Intended use

Credit risk assessment for retail loan applications. It provides the probability of serious delinquency within two years ($d1q\_2yrs$) to support human case workers in making loan approval or rejection decisions. It must not be used as an autonomous credit decision engine or applied to institutional corporate credit.

## Data

Credit Risk Benchmark dataset containing 16,712 observations across 10 numerical features. Preprocessing removed records containing missing targets and special delinquency sentinel codes (96 and 98). Continuous numerical variables were scaled using training-split statistics. The dataset was partitioned via stratified split into 70% training, 15% validation, and 15% test sets.

## Metric

Area Under the ROC Curve (`val/auc` and `test/auc`), because credit risk data exhibits class imbalance and the metric evaluates discrimination across all operating thresholds independent of decision boundaries.

## Threshold

0.5 for every team. At this threshold, the model flags applicants with a predicted delinquency probability $\ge 0.5$ as high risk. On the test set (2,507 samples), it refused 1,218 applicants (48.6%), correctly identifying 913 true delinquents while yielding 305 false positives.

## Results

Evaluation on the identical validation split and held-out test split:

| Candidate | Version | Threshold | val/auc | test/auc | test/TP | test/FN | test/FP | test/TN |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| Baseline | gaspar-baseline-v1 | 0.35 | 0.7688 | 0.7647 | 748 | 493 | 278 | 975 |
| Logistic Regression | model-a:v0 | 0.50 | 0.8067 | 0.8043 | 890 | 351 | 313 | 940 |
| **Random Forest** | **model-a:v1** | **0.50** | **0.8134** | **0.8102** | **913** | **328** | **305** | **948** |

Across all age groups, Random Forest consistently maintained higher true positive identification and lower false negative rates than the linear baseline.

## Limitations

The model is sensitive to severe shifts in macroeconomic credit cycles and borrower delinquency behaviors outside the benchmark distribution. It does not account for qualitative applicant data, unstructured salary documentation, or localized Swiss debt register certificates (delegated to Model B and Model C).

## Contact

Team Gaspar & Uchenna Desmond Okoro (ADSTA Group), October 2026.