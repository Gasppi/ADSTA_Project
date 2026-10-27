"""Every step that learns a number from the data before a model sees it."""

from typing import Final

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

# The extreme features, and the share of training values that stay below the limit.
CLIP_AT: Final = {"rev_util": 0.99, "monthly_inc": 0.99, "debt_ratio": 0.95}


class PercentileClipper(BaseEstimator, TransformerMixin):
    """Learns an upper limit per column on the training set, then cuts every set at it."""

    def __init__(self, clip_at: dict[str, float] | None = None) -> None:
        self.clip_at = clip_at

    def fit(self, X: pd.DataFrame, y: object = None) -> "PercentileClipper":
        self.limits_: dict[str, float] = {}
        for column, share in (self.clip_at or {}).items():
            self.limits_[column] = float(X[column].quantile(share))
        self.feature_names_in_ = np.array(X.columns, dtype=object)
        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        clipped = X.copy()
        for column, limit in self.limits_.items():
            clipped[column] = X[column].clip(upper=limit)
        return clipped

    def get_feature_names_out(self, input_features: object = None) -> np.ndarray:
        return self.feature_names_in_


def build_preprocessing() -> Pipeline:
    """Unfitted. Fit it on the training set only, then transform every set with it."""
    return Pipeline(
        [
            ("outliers", PercentileClipper(clip_at=CLIP_AT)),
            ("scale", StandardScaler()),
        ]
    ).set_output(transform="pandas")
