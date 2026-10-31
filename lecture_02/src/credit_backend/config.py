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

    model_c: str | None = None
    """The Ollama tag of Model C, read from MODEL_C. Without it, decisions have no wording."""

    database_url: str
    """The URL of the database, read from DATABASE_URL. It has no default, because it carries
    a password, and a password belongs in .env and never in Git."""
