# Task 6: the tests for your baseline, written before the baseline.
from credit_backend.decisions.features import FeatureVector
from credit_backend.decisions.scoring import GasparBaselineScorer


def test_gaspar_baseline_matches_hand_calculation():
    features = FeatureVector(
        age=41.0,
        dependents=1.0,
        rev_util=0.25,
        late_90=0.0,
        monthly_inc=6000.0,
        debt_ratio=0.2,
    )

    scorer = GasparBaselineScorer()

    # C.manual: 0.03 + (0.20 * 0.35) + (0.25 * 0.25) + (0.0 * 0.18) = 0.1625
    assert scorer.probability_of_default(features) == 0.1625
