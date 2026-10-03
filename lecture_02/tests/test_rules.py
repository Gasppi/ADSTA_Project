from dataclasses import replace
from typing import Final

import pytest

from credit_backend.contracts import Outcome
from credit_backend.decisions.rules import Policy, RuleInputs, decide

POLICY: Final = Policy(threshold=0.30)

# Task 4: port the fixture and the boundary test from the pytest slide here.
@pytest.fixture
def sound() -> RuleInputs:
    return RuleInputs(default_probability=0.05)

def test_a_sound_application_is_approved(sound):
    assert decide(sound, POLICY).outcome is Outcome.APPROVED


@pytest.mark.parametrize(("probability", "outcome"),
    [(0.29, Outcome.APPROVED), (0.30, Outcome.REFUSED), (0.31, Outcome.REFUSED)])
def test_threshold_boundary(sound, probability, outcome):
    inputs = replace(sound, default_probability=probability)
    assert decide(inputs, POLICY).outcome is outcome