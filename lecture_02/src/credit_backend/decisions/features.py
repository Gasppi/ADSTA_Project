"""The figures Model A works on, worked out from the confirmed application."""

from dataclasses import dataclass

from credit_backend.contracts import CaseWorkerInput


@dataclass(frozen=True)
class FeatureVector:
    """Each feature is named after its column in the training data."""

    age: float
    # Task 5: the features you picked.


def build_features(entered: CaseWorkerInput) -> FeatureVector:
    return FeatureVector(
        age=float(entered.age),
    )
