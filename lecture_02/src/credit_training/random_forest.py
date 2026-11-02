"""Model A as a random forest.

uv run python -m credit_training.random_forest
"""

from typing import Any, Final

from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import Pipeline

from credit_training import metrics
from credit_training.data import SEED, load_splits
from credit_training.preprocessing import build_preprocessing
from credit_training.tracking import TrainedModel, log_details, log_model, start_run

NAME: Final = "random-forest"
PARAMS: Final[dict[str, Any]] = {"n_estimators": 200, "max_depth": 8, "max_features": "sqrt"}


def train(params: dict[str, Any] | None = None) -> TrainedModel:
    splits = load_splits()
    with start_run(NAME, config=PARAMS | (params or {})) as run:
        params = dict(run.config)

        preprocessing = build_preprocessing().fit(splits.train.X)
        X_train = preprocessing.transform(splits.train.X)
        X_val = preprocessing.transform(splits.val.X)

        model = RandomForestClassifier(
            n_estimators=params["n_estimators"],
            max_depth=params["max_depth"],
            max_features=params["max_features"],
            random_state=SEED,
            n_jobs=-1,
        )
        model.fit(X_train, splits.train.y)

        p_val = model.predict_proba(X_val)[:, 1]
        trained = TrainedModel(
            name=NAME,
            pipeline=Pipeline([("preprocessing", preprocessing), ("model", model)]),
            score=metrics.score(splits.val.y, p_val),
        )

        log_details(run, splits, splits.val.y, p_val)
        log_model(run, trained)

    print(f"{NAME}: {metrics.KEY} = {trained.score:.3f}")
    return trained


if __name__ == "__main__":
    train()