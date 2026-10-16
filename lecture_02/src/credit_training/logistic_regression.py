"""Model A as a logistic regression.

uv run python -m credit_training.logistic_regression
"""

from typing import Any, Final

from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

from credit_training import metrics
from credit_training.data import SEED, load_splits
from credit_training.preprocessing import build_preprocessing
from credit_training.tracking import TrainedModel, log_model, start_run

NAME: Final = "logistic-regression"
PARAMS: Final[dict[str, Any]] = {"C": 1.0, "class_weight": None}


def train(params: dict[str, Any] | None = None) -> TrainedModel:
    splits = load_splits()
    with start_run(NAME, config=PARAMS | (params or {})) as run:
        params = dict(run.config)

        preprocessing = build_preprocessing().fit(splits.train.X)
        X_train = preprocessing.transform(splits.train.X)
        X_val = preprocessing.transform(splits.val.X)

        model = LogisticRegression(
            C=params["C"], class_weight=params["class_weight"], max_iter=1000, random_state=SEED
        )
        model.fit(X_train, splits.train.y)

        p_val = model.predict_proba(X_val)[:, 1]
        trained = TrainedModel(
            name=NAME,
            pipeline=Pipeline([("preprocessing", preprocessing), ("model", model)]),
            score=metrics.score(splits.val.y, p_val),
        )

        # Task 4: track this training, so that a teammate can find the run and repeat it.
        # The slide "What to log" lists what belongs in it.

        log_model(run, trained)

    print(f"{NAME}: {metrics.KEY} = {trained.score:.3f}")
    return trained


if __name__ == "__main__":
    train()
