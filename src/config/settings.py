import re
from pathlib import Path
from urllib.parse import quote

from dotenv import load_dotenv  # type: ignore
from pydantic import SecretStr, field_validator  # type: ignore
from pydantic_settings import BaseSettings, SettingsConfigDict  # type: ignore

from src import create_logger

logger = create_logger(name="settings")


def fix_url_credentials(url: str) -> str:
    """
    Fix URL by properly encoding special characters in credentials.

    Parameters
    ----------
    url : str
        The URL to fix.

    Returns
    -------
    fixed_url : str
        The fixed URL.
    """
    try:
        # More flexible pattern that accepts any scheme format
        # Captures: anything://username:password@host_and_rest
        pattern = r"^([^:]+://)([^:/?#]+):([^@]+)@(.+)$"
        match = re.match(pattern, url)

        if match:
            scheme, username, password, host_part = match.groups()
            # URL encode the username and password
            # safe='' means encode all special characters
            encoded_username = quote(username, safe="")
            encoded_password = quote(password, safe="")

            # Reconstruct the URL
            fixed_url = f"{scheme}{encoded_username}:{encoded_password}@{host_part}"

            # Extract scheme name for logging
            scheme_name = scheme.rstrip("://")  # noqa: B005
            logger.debug(f"Fixed {scheme_name!r} URL encoding for special characters")

            return fixed_url

        logger.debug("WARNING: No regex match found!")
        return url

    except Exception as e:
        logger.warning(f"Could not fix URL: {e}")
        return url


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

    # ===== DATABASE =====
    POSTGRES_USER: str = "langgraph"
    POSTGRES_PASSWORD: SecretStr = SecretStr("your_postgres_password")
    POSTGRES_DB: str = "langgraph"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432

    API_DB_NAME: str = "user_feedback_db"

    # ===== REMOTE INFERENCE =====
    # GROQ
    GROQ_API_KEY: SecretStr = SecretStr("your_groq_api_key")
    GROQ_URL: str = "https://api.groq.com/openai/v1"

    # OPENROUTER
    OPENROUTER_API_KEY: SecretStr = SecretStr("your_openrouter_api_key")
    OPENROUTER_URL: str = "https://openrouter.ai/api/v1"

    # TAVILY
    TAVILY_API_KEY: SecretStr = SecretStr("")

    # ===== OBSERVABILITY =====
    # LANGFUSE
    LANGFUSE_SECRET_KEY: SecretStr = SecretStr("your_langfuse_secret_key")
    LANGFUSE_PUBLIC_KEY: SecretStr = SecretStr("your_langfuse_public_key")
    LANGFUSE_HOST: str = "https://cloud.langfuse.com"

    # ===== API AUTHENTICATION =====
    SECRET_KEY: SecretStr = SecretStr("your_secret_key")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    @field_validator("POSTGRES_PORT", mode="before")
    @classmethod
    def parse_port_fields(cls, v: str | int) -> int:
        """Parses port fields to ensure they are integers."""
        if isinstance(v, str):
            try:
                return int(v.strip())
            except ValueError:
                raise ValueError(f"Invalid port value: {v}") from None

        if isinstance(v, int) and not (1 <= v <= 65535):
            raise ValueError(f"Port must be between 1 and 65535, got {v}")

        return v

    @property
    def database_url(self) -> str:
        """
        Constructs the API database connection URL.

        This is the database used for user authentication and API-specific tables.
        It's separate from MLflow's database to avoid conflicts.

        Returns
        -------
        str
            Complete database connection URL in the format:
            postgresql+psycopg2://user:password@host:port/dbname
        """
        url: str = (
            f"postgresql+psycopg2://{self.POSTGRES_USER}"
            f":{self.POSTGRES_PASSWORD.get_secret_value()}"
            f"@{self.POSTGRES_HOST}"
            f":{self.POSTGRES_PORT}"
            f"/{self.POSTGRES_DB}"
        )
        return fix_url_credentials(url)

    @property
    def database_url_2(self) -> str:
        """
        Constructs the API database connection URL.

        This is the database used for user authentication and API-specific tables.
        It's separate from MLflow's database to avoid conflicts.

        Returns
        -------
        str
            Complete database connection URL in the format:
            postgresql+psycopg2://user:password@host:port/dbname
        """
        url: str = (
            f"postgresql+psycopg2://{self.POSTGRES_USER}"
            f":{self.POSTGRES_PASSWORD.get_secret_value()}"
            f"@{self.POSTGRES_HOST}"
            f":{self.POSTGRES_PORT}"
            f"/{self.API_DB_NAME}"
        )
        return fix_url_credentials(url)


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
