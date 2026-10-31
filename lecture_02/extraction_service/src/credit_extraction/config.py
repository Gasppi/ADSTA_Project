"""Which Model B the service loads. Nothing here has a default."""

from pydantic import ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="MODEL_B_", use_attribute_docstrings=True)

    checkpoint: str
    """The name of your Model B on the Hugging Face Hub, read from MODEL_B_CHECKPOINT."""

    revision: str
    """The commit hash Model B is pinned to, read from MODEL_B_REVISION. It has no default."""


def load_settings() -> Settings:
    """Stops the service at start when a setting is missing, rather than at the first request."""
    try:
        return Settings()
    except ValidationError as error:
        missing = ", ".join(f"MODEL_B_{str(one['loc'][0]).upper()}" for one in error.errors())
        raise SystemExit(f"Task 3: set {missing} to the Model B you chose.") from error