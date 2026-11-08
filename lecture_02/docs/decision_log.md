# Decision log: Model A (lecture 3)
---
model: model-a
registry: wandb-registry-model/model-a
version: v5
run: lohcaawu (random-forest-run)
commit: 715cbd9
---

## Task 1: bring in the training job
- `build_baseline()` returns `GasparBaselineScorer`.
- The web conflict editor corrupted `uv.lock`. It was deleted and regenerated with `uv lock`.
- The lecture 3 PR renamed the `FeatureVector` fields (`rev_util`, `monthly_inc`, `dependents`). The baseline and its test were updated.

## Task 2: preprocessing (Desmond)
- `PercentileClipper` learns its limits on the training set only: p99 for `rev_util` and `monthly_inc`, p95 for `debt_ratio`, because all three are heavily right-skewed. Then `StandardScaler`, fitted on train only.
- Not `RobustScaler`: the `late_*` columns are mostly zeros, so their IQR is 0.
- data.py drops 2 duplicate rows and 88 rows with the codes 96/98 in any late_* column before the split, so the clipper and scaler never see them.
- p95 for `debt_ratio`: its 99th percentile is 607, about 480 times its 95th percentile (1.264), so p99 would keep the extreme values; p95 cuts them back.

## Task 3: metric
- First choice was ROC AUC. After Desmond's review it changed to **F1 at the fixed 0.5 threshold**: the task requires a metric that judges models at the 0.5 line, and AUC ignores it. F1 fits because both a missed default and a wrongly refused applicant are costly.
- AUC, recall, precision and average precision are logged as secondary numbers.
- The test set was seen once with AUC before the change. The model was chosen on validation F1 only.

## Task 4: tracking
- Each run logs the config (settings, `split_seed` and `model_seed` 42, threshold, features, `n_train`, `n_val`), the secondary metrics, the confusion matrix, `uv.lock` and the model artifact. Runs are named `<model>-run`.
- The W&B team comes from `WANDB_ENTITY`.
- Not logged: a hash of the dataset.

## Task 5: random forest
- Same split, preprocessing, seed and metric as the logistic regression. Defaults: 200 trees, `max_depth` 8, `max_features` "sqrt".

## Task 6: sweeps
- Logistic regression searches `C` (log-uniform 0.001 to 100) and `class_weight`. The forest searches `n_estimators`, `max_depth` and `max_features` ("sqrt", 0.5, None).
- `log2` was dropped from `max_features`: with 6 features it equals `sqrt` (2 features per split).
- A Bayesian sweep on the forest stalled after 2 runs, so the final sweeps used random search (15 runs for the logistic regression, 20 for the forest), on the F1 metric.
- Best validation F1: 0.724 (logistic regression, v4) and 0.736 (forest, v5). Earlier AUC sweeps are kept in the registry as v1 to v3.
- Tuning moved AUC by less than 0.01, so the limit is the 6 features, not the settings.

## Task 7: comparison and promotion
- Validation F1: baseline 0.667, logistic regression 0.724, forest 0.736. The forest was chosen on validation only.
- Test F1, reported once: forest 0.743, logistic regression 0.729, baseline 0.660.
- `model-a:v5` was promoted to `production` with `credit_training.registry promote random-forest`.

## Task 8: backend
- With `MODEL_A=wandb-registry-model/model-a:production`, `POST /decisions` returned 200 with `model_version` `model-a:v5`, probability 0.295 and outcome approved.

## Known limits
- Only 6 of 10 features are used. The dropped 96/98 rows were 94% defaults.
- The baseline uses 0.35, the models 0.5.
- One split and one seed, so the 0.012 F1 gap is not proven.