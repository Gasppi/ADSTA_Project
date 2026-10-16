"""Every step that learns a number from the data before a model sees it."""

from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer


def build_preprocessing() -> Pipeline:
    """Unfitted. Fit it on the training set only, then transform every set with it."""
    return Pipeline(
        [
            # Task 2: handle the extreme values you found in the EDA. Learn any limit on the
            # training set, in fit, and only apply it in transform.
            ("outliers", FunctionTransformer(feature_names_out="one-to-one")),
            # Task 2: the scaler you chose. Until then, both steps pass the data through unchanged.
            ("scale", FunctionTransformer(feature_names_out="one-to-one")),
        ]
    ).set_output(transform="pandas")
