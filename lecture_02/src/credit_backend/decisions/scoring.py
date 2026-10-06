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
    def threshold(self) -> int:
        return 0.30

    def probability_of_default(self, features: FeatureVector) -> float:
        return 0.10


class BaselineScorer(Scorer):
    """A hand-built estimate using debt ratio, severe lateness, and dependants."""

    @property
    def model_version(self) -> str:
        return "baseline-v1"

    @property
    def threshold(self) -> float:
        return 0.30
    def probability_of_default(self, features: FeatureVector) -> float:
        debt_ratio = features.debt_ratio if features.debt_ratio is not None else 0.6
        return 0.05 + (debt_ratio * 0.5) + (features.late_90 * 0.15) + (features.dependants * 0.02)