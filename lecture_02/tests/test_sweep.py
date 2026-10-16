from typing import Any

import pytest

from credit_training.sweep import MODELS, SEARCH_SPACES


def search_space(model: str) -> dict[str, Any]:
    if not SEARCH_SPACES[model]:
        pytest.skip(f"Task 6: there are no settings to search for {model} yet")
    return SEARCH_SPACES[model]


@pytest.mark.parametrize("model", MODELS)
def test_a_sweep_only_searches_settings_the_training_reads(model: str) -> None:
    unknown = set(search_space(model)) - set(MODELS[model].PARAMS)

    assert not unknown, f"{sorted(unknown)} are not in the PARAMS of {model}"


@pytest.mark.parametrize("model", MODELS)
def test_every_searched_setting_says_which_values_to_try(model: str) -> None:
    for setting, values in search_space(model).items():
        assert {"value", "values", "distribution", "min"} & set(values), setting
