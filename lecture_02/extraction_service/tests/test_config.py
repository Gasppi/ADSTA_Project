import pytest
from credit_extraction.config import Settings, load_settings


def test_a_service_with_no_model_b_stops_at_start_and_names_the_setting(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("MODEL_B_CHECKPOINT", raising=False)

    with pytest.raises(SystemExit, match="MODEL_B_CHECKPOINT"):
        load_settings()


def test_model_b_is_pinned_to_one_revision(monkeypatch: pytest.MonkeyPatch) -> None:
    if "revision" not in Settings.model_fields:
        pytest.skip("Task 3: Model B is not pinned to a revision yet")
    monkeypatch.setenv("MODEL_B_CHECKPOINT", "your-team/model-b")
    monkeypatch.delenv("MODEL_B_REVISION", raising=False)

    with pytest.raises(SystemExit, match="MODEL_B_REVISION"):
        load_settings()

    monkeypatch.setenv("MODEL_B_REVISION", "0123abc")

    assert load_settings().revision == "0123abc"  # ty: ignore[unresolved-attribute]
