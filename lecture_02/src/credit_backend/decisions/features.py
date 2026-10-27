"""The figures Model A works on, worked out from the confirmed application."""

from dataclasses import dataclass

from credit_backend.contracts import CaseWorkerInput


@dataclass(frozen=True)
class FeatureVector:
    """Each feature is named after its column in the training data."""

    age: float
    dependents: float
    rev_util: float
    late_90: float
    monthly_inc: float | None
    debt_ratio: float | None


def build_features(entered: CaseWorkerInput) -> FeatureVector:
    income = entered.monthly_income
    monthly_inc = float(income.as_monthly().amount) if income is not None else None
    debt_ratio = (
        float(entered.monthly_debt_obligations) / monthly_inc if monthly_inc is not None else None
    )
    return FeatureVector(
        age=float(entered.age),
        dependents=float(entered.dependants),
        rev_util=entered.revolving_utilisation,
        late_90=float(entered.late_90),
        monthly_inc=monthly_inc,
        debt_ratio=debt_ratio,
    )
