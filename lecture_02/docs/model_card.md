---
model: model-a
registry: wandb-registry-model/model-a
version: v5
run: <run id of the random-forest run behind v5, from the W&B Overview>
commit: <commit hash from the same Overview>
---

# Model A: probability of default

## Intended use

Credit risk assessment for retail loan applications. The model gives the probability of serious delinquency within two years (`dlq_2yrs`) to support human case workers in approving or rejecting a loan. It must not be used as an autonomous credit decision engine, or for corporate credit.

## Data

Credit Risk Benchmark dataset: 16,714 raw rows, 10 numerical features and the target dlq_2yrs.
Cleaning removed 2 duplicate rows and 88 rows with the sentinel codes 96 or 98 in a late_* column (94% of the coded rows were defaults, so the model has not seen this kind of applicant), leaving 16,624 rows. 
After cleaning, a stratified split with seed 42 gives 11,636 training, 2,494 validation and 2,494 test rows (16,624 in total).

## Metric

F1 of the decisions at the fixed 0.5 threshold (`val/f1`). The task requires a metric that judges models at the 0.5 line. F1 fits because a missed default and a wrongly refused applicant are both costly. ROC AUC, recall, precision and average precision are logged as secondary numbers.

## Threshold

0.5 for every team. On the test set the model refuses 1,258 of 2,494 applicants (50.4%): 928 of 1,241 defaulters are caught (recall 0.748) and 330 good applicants are refused (precision 0.738).

## Results

Same split and same seed for every candidate. The model was chosen on validation F1 only.

| Candidate | Version | Threshold | val/f1 | test/f1 | test/TP | test/FN | test/FP | test/TN |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| Baseline | gaspar-baseline-v1 | 0.35 | 0.667 | 0.660 | 748 | 493 | 278 | 975 |
| Logistic regression | model-a:v4 | 0.50 | 0.724 | 0.729 | 891 | 350 | 312 | 941 |
| **Random forest** | **model-a:v5** | **0.50** | **0.736** | **0.743** | **928** | **313** | **330** | **923** |

Both learned models beat the baseline by 0.06 to 0.07 F1. The forest leads the logistic regression by 0.012 F1 on validation. This was measured on one split and one seed, so the gap is not proven.

Results per group (for example per age band) have not been computed.

## Limitations

- Only 6 of the 10 features are used. Tuning moved AUC by less than 0.01, so the features limit the model, not the settings.
- Applicants with the codes 96/98 were removed. They were mostly defaulters, and the model has not seen them.
- The baseline uses its own threshold (0.35), the learned models use 0.5, so their decisions are not directly comparable.
- The test set was seen once earlier, with AUC, before the metric changed to F1 after review. The choice does not depend on it.
- No fairness check per group. Qualitative applicant data, documents and Swiss debt register certificates are outside this model (Models B and C).

## Contact

Gaspar De Fernandez Herrera and Desmond Okoro (ADSTA), November 2026.