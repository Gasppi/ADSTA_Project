"""The figures Model A works on, worked out from the confirmed application."""

from dataclasses import dataclass

from credit_backend.contracts import CaseWorkerInput


@dataclass(frozen=True)
class FeatureVector:
    """Each feature is named after its column in the training data."""

    age: float
    dependants: float
    revolving_utilisation: float
    late_90: float
    monthly_income: float | None
    monthly_debt_obligations: float
    debt_ratio: float | None
    # Task 5: Correct features picked.


def build_features(entered: CaseWorkerInput) -> FeatureVector:
    return FeatureVector(
        age=float(entered.age),
        dependants=float(entered.dependants),
        revolving_utilisation=entered.revolving_utilisation,
        late_90=float(entered.late_90),
        monthly_income=(
            float(entered.monthly_income.as_monthly().amount)
            if entered.monthly_income is not None
            else None
        ),
        monthly_debt_obligations=float(entered.monthly_debt_obligations),
        debt_ratio=(
            float(entered.monthly_debt_obligations)
            / float(entered.monthly_income.as_monthly().amount)
            if entered.monthly_income is not None
            else None
        ),
    )
