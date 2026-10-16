from typing import Final

import numpy as np

from credit_training import metrics

DEFAULTED: Final = np.array([1, 1, 1, 1, 0, 0, 0, 0, 0, 0])
RANKED_PERFECTLY: Final = np.array([0.95, 0.9, 0.8, 0.6, 0.45, 0.4, 0.35, 0.3, 0.2, 0.1])


def better(first: float, second: float) -> bool:
    return first > second if metrics.GOAL == "maximize" else first < second


def test_the_metric_is_one_number() -> None:
    assert isinstance(metrics.score(DEFAULTED, RANKED_PERFECTLY), float)


def test_a_model_that_ranks_perfectly_beats_one_that_ranks_backwards() -> None:
    perfect = metrics.score(DEFAULTED, RANKED_PERFECTLY)
    backwards = metrics.score(DEFAULTED, 1 - RANKED_PERFECTLY)

    assert better(perfect, backwards)
