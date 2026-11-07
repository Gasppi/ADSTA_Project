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

Lecture 3: 
Task 1, bring in the job: build_baseline() returns GasparBaselineScorer. The web conflict editor corrupted uv.lock, so it was deleted and regenerated with uv lock. The lecture 3 PR renamed the FeatureVector fields (rev_util, monthly_inc, dependents), so the baseline and its test were updated.
Task 2, preprocessing (Desmond): PercentileClipper learns its limits on train only, at p99 for rev_util and monthly_inc and p95 for debt_ratio, because all three are heavily right-skewed. Then StandardScaler, fitted on train only. Not RobustScaler, because the late_* columns are mostly zeros (IQR 0). Codes 96/98 are dropped upstream in data.py. [Reason for p95 on debt_ratio: ask Desmond.]
Task 3, metric: first AUC, then changed to F1 at the fixed 0.5 threshold after Desmond’s review. The reason is that the task requires a metric that judges models at the 0.5 line, which AUC ignores. F1 fits because a missed default and a wrongly refused applicant are both costly. AUC, recall, precision and AP are logged as secondary numbers. The test set was seen once earlier, with AUC. The model was chosen on validation F1 only.
Task 4, tracking: each run logs the config (settings, split_seed and model_seed 42, threshold, features, n_train and n_val), the secondary metrics, the confusion matrix, uv.lock and the model artifact. Runs are named <model>-run. The W&B team is the one in WANDB_ENTITY. [Not logged: the dataset hash, so say so or add it.]
Task 5, random forest: same split, preprocessing, seed and metric as the logistic regression. Defaults are 200 trees, max_depth 8 and max_features “sqrt”.
Task 6, sweeps:
Logistic regression searches C (log-uniform 0.001 to 100) and class_weight.
Forest searches n_estimators, max_depth and max_features (“sqrt”, 0.5, None). log2 was dropped because it equals sqrt with 6 features.
The first forest sweep with Bayesian search stalled after 2 runs, so both final sweeps used random search (15 runs and 20 runs).
Best validation F1 is 0.724 (logistic regression, v4) and 0.736 (forest, v5).
Tuning moved AUC by less than 0.01, so the limit is the 6 features, not the settings.
Task 7, comparison: validation F1 is baseline 0.667, logistic regression 0.724 and forest 0.736. The forest was chosen. Test F1 reported once: 0.743 (baseline 0.660, logistic regression 0.729). model-a:v5 was promoted to production.
Task 8, backend: with MODEL_A set to production, POST /decisions returned 200 with model_version model-a:v5, probability 0.295 and outcome approved.
Known limits: only 6 of 10 features are used, the dropped 96/98 rows were 94% defaults, and the baseline uses 0.35 while the models use 0.5. One split and one seed, so the 0.012 F1 gap is not proven.