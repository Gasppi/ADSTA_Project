"""What the backend reads from the environment when it starts."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(use_attribute_docstrings=True, env_ignore_empty=True)

    model_a: str | None = None
    """The registered Model A, read from MODEL_A. Without it, the baseline scores."""

    extraction_url: str = "http://localhost:8001"
    """Where the Information Extraction Service answers, read from EXTRACTION_URL."""

    ollama_url: str = "http://localhost:11434"
    """Where Ollama answers, read from OLLAMA_URL."""

    # Task 6: the Ollama tag of your Model C, read from MODEL_C. Write no tag into the code.
    # When MODEL_C is not set, the value is None.

    # Task 7b: the URL of your database, read from DATABASE_URL. Give it no default, because
    # it carries a password, and a password belongs in .env and never in Git.
