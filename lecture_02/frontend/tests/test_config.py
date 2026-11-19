import pytest

from credit_frontend.config import ConfigError, Settings, load_settings

ENVIRONMENT = {
    "BACKEND_URL": "http://backend:8000",
    "EXTRACTION_TIMEOUT_SECONDS": "200",
    "DECISION_TIMEOUT_SECONDS": "90",
}


def test_the_three_values_are_read_from_the_environment() -> None:
    assert load_settings(ENVIRONMENT) == Settings(
        backend_url="http://backend:8000",
        extraction_timeout_seconds=200.0,
        decision_timeout_seconds=90.0,
    )


@pytest.mark.parametrize("name", list(ENVIRONMENT))
def test_none_of_them_has_a_default(name: str) -> None:
    environment = {key: value for key, value in ENVIRONMENT.items() if key != name}

    with pytest.raises(ConfigError, match=name):
        load_settings(environment)


@pytest.mark.parametrize("name", list(ENVIRONMENT))
def test_an_empty_value_counts_as_missing(name: str) -> None:
    with pytest.raises(ConfigError, match=name):
        load_settings(ENVIRONMENT | {name: " "})


@pytest.mark.parametrize("raw", ["ninety", "0", "-5"])
def test_a_timeout_must_be_a_number_of_seconds_above_zero(raw: str) -> None:
    with pytest.raises(ConfigError, match="DECISION_TIMEOUT_SECONDS"):
        load_settings(ENVIRONMENT | {"DECISION_TIMEOUT_SECONDS": raw})
