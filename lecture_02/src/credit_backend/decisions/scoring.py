"""Where the probability of default comes from."""

from typing import Protocol

from credit_backend.decisions.features import FeatureVector


class Scorer(Protocol):
    @property
    def model_version(self) -> str: ...

    @property
    def threshold(self) -> float: ...

    def probability_of_default(self, features: FeatureVector) -> float: ...


class PlaceholderScorer(Scorer):
    """The same probability for every applicant."""

    @property
    def model_version(self) -> str:
        return "placeholder"

    @property
    def threshold(self) -> float:
        return 0.30

    def probability_of_default(self, features: FeatureVector) -> float:
        return 0.10


# Task 6: each of you adds a scorer here, such as BaselineScorer(Scorer). It works out a
# probability of default by hand from the features, until Model A replaces it in lecture 3.
# Ask yourself: if I judged an applicant from these features alone, which figures would
# worry me, and how much?

class GasparBaselineScorer(Scorer):
    """Hand-built credit risk estimate incorporating debt ratio, revolving utilisation, and severe lateness."""

    @property
    def model_version(self) -> str:
        return "gaspar-baseline-v1"

    @property
    def threshold(self) -> float:
        return 0.35

    def probability_of_default(self, features: FeatureVector) -> float:
        debt_ratio = features.debt_ratio if features.debt_ratio is not None else 0.50
        revolving_util = (
            features.revolving_utilisation
            if features.revolving_utilisation is not None
            else 0.30
        )
        late_90 = features.late_90 if features.late_90 is not None else 0.0

        raw_prob = (
            0.03
            + (debt_ratio * 0.35)
            + (revolving_util * 0.25)
            + (late_90 * 0.18)
        )

        return max(0.0, min(1.0, round(raw_prob, 4)))


    #Comment task8 just to check if the test is working
