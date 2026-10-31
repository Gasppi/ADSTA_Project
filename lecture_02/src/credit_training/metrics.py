"""The one metric every candidate for Model A is judged by."""

from typing import Final, Literal

from numpy.typing import ArrayLike
from sklearn.metrics import roc_auc_score

# Every model refuses an applicant from this probability of default up.
THRESHOLD: Final = 0.5

NAME: Final = "auc"
GOAL: Final[Literal["maximize", "minimize"]] = "maximize"
KEY: Final = f"val/{NAME}"


def score(y_true: ArrayLike, p_default: ArrayLike, threshold: float = THRESHOLD) -> float:
    """ROC AUC of the predicted probabilities. It ranks applicants, so the threshold is unused."""
    del threshold
    return float(roc_auc_score(y_true, p_default))
