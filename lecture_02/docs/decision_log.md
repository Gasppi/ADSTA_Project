# Architectural Decision Log: Model A Training, Sweeps & Registry

## ADR 1: Preprocessing & Outlier Handling (Task 2)
- **Context:** Features like `monthly_inc` and `debt_ratio` are skewed with extreme values, while sentinel codes `96` and `98` in late-payment columns distort numerical distributions.
- **Decision:** Dropped sentinel rows containing codes `96` and `98`. Scaled numerical features using statistics fitted exclusively on the 70% training split to prevent target leakage into validation and test sets.
- **Status:** Implemented & Verified.

## ADR 2: Evaluation Metric Selection (Task 3)
- **Context:** The credit risk dataset contains substantial class imbalance, making standard accuracy misleading (predicting all negative achieves high accuracy but misses true delinquencies).
- **Decision:** Selected Area Under the ROC Curve (`val/auc` and `test/auc`) as the primary evaluation metric. ROC-AUC evaluates true positive vs. false positive trade-offs across all potential decision thresholds independent of the fixed 0.5 classification cutoff.
- **Status:** Implemented & Verified.

## ADR 3: Hyperparameter Sweeps & Architecture Search (Task 6)
- **Context:** Comparing linear baseline vs. tree ensemble challenger models.
- **Decision:** Conducted 5-trial Bayesian optimization sweeps for both `logistic-regression` (optimizing `C` and `class_weight`) and `random-forest` (optimizing `n_estimators`, `max_depth`, and `max_features`) logged to W&B workspace `desmonduchenna503-university-of-luzern/credit-model-a`.
- **Status:** Implemented & Verified.

## ADR 4: Model Promotion to Production (Task 7)
- **Context:** Final evaluation on identical validation and held-out test splits.
- **Evaluation Outcomes:**
  - Baseline (`gaspar-baseline-v1`): `val/auc = 0.7688`, `test/auc = 0.7647`
  - Logistic Regression (`model-a:v0`): `val/auc = 0.8067`, `test/auc = 0.8043`
  - Random Forest (`model-a:v1`): `val/auc = 0.8134`, `test/auc = 0.8102` (test TP = 913, test FP = 305)
- **Decision:** Promoted `random-forest` (version `v1`) to `production` via `credit_training.registry promote random-forest`. The random forest model minimized false negatives (328 vs 351) while delivering superior test discrimination over logistic regression.
- **Status:** Promoted in W&B Model Registry.