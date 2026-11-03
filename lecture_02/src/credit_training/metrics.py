"""The one metric every candidate for Model A is judged by."""

from typing import Final, Literal

import numpy as np
from numpy.typing import ArrayLike
from sklearn.metrics import f1_score

# Every model refuses an applicant from this probability of default up.
THRESHOLD: Final = 0.5

NAME: Final = "f1"
GOAL: Final[Literal["maximize", "minimize"]] = "maximize"
KEY: Final = f"val/{NAME}"


def score(y_true: ArrayLike, p_default: ArrayLike, threshold: float = THRESHOLD) -> float:
    """F1 of the decisions, refusing from the threshold up."""
    refused = np.asarray(p_default) >= threshold
    return float(f1_score(y_true, refused))