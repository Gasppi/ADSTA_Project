from pathlib import Path
from types import ModuleType

import numpy as np
import pandas as pd
import pytest

from credit_backend.decisions.features import FeatureVector
from credit_backend.decisions.scoring import RegisteredScorer
from credit_training import logistic_regression, metrics, random_forest
from credit_training.data import Splits, load_splits
from credit_training.preprocessing import build_preprocessing
from credit_training.tracking import TrainedModel, save_model

MODELS = pytest.mark.parametrize(
    "module", [logistic_regression, random_forest], ids=lambda module: module.NAME
)


@pytest.fixture(autouse=True)
def without_tracking(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WANDB_MODE", "disabled")


@pytest.fixture(scope="module")
def splits() -> Splits:
    return load_splits()


def train(module: ModuleType) -> TrainedModel:
    try:
        return module.train()
    except NotImplementedError as error:
        pytest.skip(str(error))


@MODELS
def test_the_model_gives_every_applicant_a_probability(module: ModuleType, splits: Splits) -> None:
    trained = train(module)

    p_default = trained.pipeline.predict_proba(splits.val.X)[:, 1]

    assert ((p_default >= 0.0) & (p_default <= 1.0)).all()


@MODELS
def test_the_same_training_gives_the_same_model(module: ModuleType, splits: Splits) -> None:
    first, second = train(module), train(module)

    np.testing.assert_allclose(
        first.pipeline.predict_proba(splits.val.X),
        second.pipeline.predict_proba(splits.val.X),
        rtol=0,
        atol=1e-12,
    )


@MODELS
def test_the_preprocessing_learns_from_the_training_set_only(
    module: ModuleType, splits: Splits
) -> None:
    trained = train(module)
    if "preprocessing" not in trained.pipeline.named_steps:
        pytest.skip(f"{module.NAME} has no preprocessing")

    learned = trained.pipeline.named_steps["preprocessing"].transform(splits.val.X)
    on_training_rows = build_preprocessing().fit(splits.train.X).transform(splits.val.X)

    pd.testing.assert_frame_equal(learned, on_training_rows)


@MODELS
def test_the_backend_scores_an_applicant_as_the_training_did(
    module: ModuleType, splits: Splits, tmp_path: Path
) -> None:
    trained = train(module)
    save_model(trained, tmp_path)
    applicant = splits.val.X.head(1)

    scorer = RegisteredScorer(tmp_path, version="test")
    probability = scorer.probability_of_default(FeatureVector(**applicant.iloc[0].to_dict()))

    assert probability == pytest.approx(trained.pipeline.predict_proba(applicant)[0, 1])
    assert scorer.threshold == metrics.THRESHOLD
