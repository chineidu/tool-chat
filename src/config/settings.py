from pathlib import Path

from dotenv import load_dotenv  # type: ignore
from pydantic import SecretStr  # type: ignore
from pydantic_settings import BaseSettings, SettingsConfigDict  # type: ignore


class BaseSettingsConfig(BaseSettings):
    """Base configuration class for settings.

    This class extends BaseSettings to provide common configuration options
    for environment variable loading and processing.

    Attributes
    ----------
    model_config : SettingsConfigDict
        Configuration dictionary for the settings model specifying env file location,
        encoding and other processing options.
    """

    model_config = SettingsConfigDict(
        env_file=str(Path(".env").absolute()),
        env_file_encoding="utf-8",
        from_attributes=True,
        populate_by_name=True,
    )


class Settings(BaseSettingsConfig):
    """Application settings class containing database and other credentials."""

    # ===== REMOTE INFERENCE =====
    # GROQ
    GROQ_API_KEY: SecretStr = SecretStr("")

    # OPENROUTER
    OPENROUTER_API_KEY: SecretStr = SecretStr("")
    OPENROUTER_URL: str = "https://openrouter.ai/api/v1"

    # TAVILY
    TAVILY_API_KEY: SecretStr = SecretStr("")

    # ===== OBSERVABILITY =====
    # LANGFUSE
    LANGFUSE_SECRET_KEY: SecretStr = SecretStr("")
    LANGFUSE_PUBLIC_KEY: SecretStr = SecretStr("")
    LANGFUSE_HOST: str = "https://cloud.langfuse.com"


def refresh_settings() -> Settings:
    """Refresh environment variables and return new Settings instance.

    This function reloads environment variables from .env file and creates
    a new Settings instance with the updated values.

    Returns
    -------
    Settings
        A new Settings instance with refreshed environment variables
    """
    load_dotenv(override=True)
    return Settings()


app_settings: Settings = refresh_settings()
