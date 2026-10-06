# Task 5: the tests features
from credit_backend.contracts import CaseWorkerInput
from credit_backend.decisions.features import build_features


def test_debt_ratio_is_debt_over_income():
    entered = CaseWorkerInput(
        age=34,
        dependants=1,
        open_credit_lines=3,
        real_estate_lines=0,
        late_30_59=0,
        late_60_89=0,
        late_90=0,
        revolving_utilisation=0.25,
        monthly_debt_obligations="1200.00",
        monthly_income={"amount": "6000.00", "currency": "CHF", "period": "monthly"},
    )

    features = build_features(entered)

    assert features.debt_ratio == 0.2
def test_missing_income_gives_none_debt_ratio():
    entered = CaseWorkerInput(
        age=34,
        dependants=1,
        open_credit_lines=3,
        real_estate_lines=0,
        late_30_59=0,
        late_60_89=0,
        late_90=0,
        revolving_utilisation=0.25,
        monthly_debt_obligations="1200.00",
        monthly_income=None,
    )

    features = build_features(entered)

    assert features.monthly_income is None
    assert features.debt_ratio is None