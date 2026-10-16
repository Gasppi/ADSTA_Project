"""The one metric every candidate for Model A is judged by."""

from typing import Final, Literal

import numpy as np
from numpy.typing import ArrayLike
from sklearn.metrics import accuracy_score

# Every model refuses an applicant from this probability of default up.
THRESHOLD: Final = 0.5

# Task 3: replace accuracy with the metric you chose, here and in score below. Set GOAL to
# "minimize" if a lower value is better. Argue for your choice in the decision log.
NAME: Final = "accuracy"
GOAL: Final[Literal["maximize", "minimize"]] = "maximize"
KEY: Final = f"val/{NAME}"


def score(y_true: ArrayLike, p_default: ArrayLike, threshold: float = THRESHOLD) -> float:
    """The metric for the predicted probabilities of default, refusing from the threshold up."""
    refused = np.asarray(p_default) >= threshold
    return float(accuracy_score(y_true, refused))
