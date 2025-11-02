from __future__ import annotations

from pathlib import Path

from omegaconf import DictConfig, OmegaConf
from pydantic import Field

from src import PACKAGE_PATH
from src.schemas import BaseSchema
from src.schemas.types import ModelProviders, RemoteModel


class CreativeModelConfig(BaseSchema):
    """Configuration for creative model."""

    model_name: str | RemoteModel = Field(
        ..., description="The name of the creative LLM to use."
    )
    model_provider: str | ModelProviders = Field(
        ..., description="The provider of the creative LLM."
    )
    temperature: float = Field(
        0.7, description="The temperature setting for the creative LLM."
    )
    max_tokens: int = Field(
        1024, description="The maximum number of tokens for the creative LLM response."
    )


class StructuredOutputModelConfig(BaseSchema):
    """Configuration for structured output model."""

    model_name: str | RemoteModel = Field(
        ..., description="The name of the structured output LLM to use."
    )
    model_provider: str | ModelProviders = Field(
        ..., description="The provider of the structured output LLM."
    )
    temperature: float = Field(
        0.0, description="The temperature setting for the structured output LLM."
    )
    max_tokens: int = Field(
        512,
        description="The maximum number of tokens for the structured output LLM response.",
    )


class LLMModelConfig(BaseSchema):
    """Configuration for models."""

    creative_model: CreativeModelConfig = Field(
        description="Creative model configuration."
    )
    structured_output_model: StructuredOutputModelConfig = Field(
        description="Structured output model configuration."
    )


class Server(BaseSchema):
    """Server configuration class."""

    host: str
    port: int
    workers: int
    reload: bool


class CORS(BaseSchema):
    """CORS configuration class."""

    allow_origins: list[str]
    allow_credentials: bool
    allow_methods: list[str]
    allow_headers: list[str]


class Middleware(BaseSchema):
    """Middleware configuration class."""

    cors: CORS


class APIConfig(BaseSchema):
    """API-level configuration."""

    title: str = Field(..., description="The title of the API.")
    name: str = Field(..., description="The name of the API.")
    description: str = Field(..., description="The description of the API.")
    version: str = Field(..., description="The version of the API.")
    status: str = Field(..., description="The current status of the API.")
    prefix: str = Field(..., description="The prefix for the API routes.")
    auth_prefix: str = Field(
        ..., description="The prefix for the authentication routes."
    )
    server: Server = Field(description="Server configuration.")
    middleware: Middleware = Field(description="Middleware configuration.")


class AppConfig(BaseSchema):
    """Application-level configuration."""

    llm_model_config: LLMModelConfig = Field(description="LLM model configurations.")
    api_config: APIConfig = Field(description="API configurations.")


config_path: Path = PACKAGE_PATH / "src/config/config.yaml"
config: DictConfig = OmegaConf.load(config_path).config
# # Resolve all the variables
resolved_cfg = OmegaConf.to_container(config, resolve=True)
# Validate the config
app_config: AppConfig = AppConfig(**dict(resolved_cfg))  # type: ignore
