from pathlib import Path

import joblib
import pandas as pd
import pytest

from credit_training.data import Splits, load_splits
from credit_training.preprocessing import build_preprocessing


@pytest.fixture(scope="module")
def splits() -> Splits:
    return load_splits()


def test_the_preprocessing_keeps_every_row_and_every_feature(splits: Splits) -> None:
    transformed = build_preprocessing().fit(splits.train.X).transform(splits.val.X)

    assert list(transformed.columns) == list(splits.val.X.columns)
    assert transformed.index.equals(splits.val.X.index)
    assert transformed.notna().all().all()


def test_a_row_is_transformed_the_same_whatever_rows_come_with_it(splits: Splits) -> None:
    preprocessing = build_preprocessing().fit(splits.train.X)

    alone = preprocessing.transform(splits.val.X.head(1))
    together = preprocessing.transform(splits.val.X).head(1)

    pd.testing.assert_frame_equal(alone, together)


def test_the_fitted_preprocessing_survives_saving_and_loading(
    splits: Splits, tmp_path: Path
) -> None:
    preprocessing = build_preprocessing().fit(splits.train.X)
    joblib.dump(preprocessing, tmp_path / "preprocessing.joblib")

    loaded = joblib.load(tmp_path / "preprocessing.joblib")

    pd.testing.assert_frame_equal(
        loaded.transform(splits.val.X), preprocessing.transform(splits.val.X)
    )
