import pytest
from pydantic import ValidationError

from credit_backend.clients.wording import WordingClient
from credit_backend.config import Settings
from credit_backend.decisions.dependencies import build_wording


def test_the_database_url_comes_from_the_environment_and_nowhere_else(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    if "database_url" not in Settings.model_fields:
        pytest.skip("Task 7b: Settings has no database URL yet")
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(ValidationError):
        Settings()


def test_a_backend_with_no_model_c_decides_without_wording(monkeypatch: pytest.MonkeyPatch) -> None:
    if "model_c" not in Settings.model_fields:
        pytest.skip("Task 6: Settings has no Model C yet")
    monkeypatch.setenv("DATABASE_URL", "sqlite://")
    monkeypatch.delenv("MODEL_C", raising=False)

    assert build_wording(Settings()) is None

    monkeypatch.setenv("MODEL_C", "your-model-c:tag")

    wording = build_wording(Settings())
    assert isinstance(wording, WordingClient)
    assert wording.model == "your-model-c:tag"
