from __future__ import annotations

from pathlib import Path

from omegaconf import DictConfig, OmegaConf
from pydantic import Field

from src import PACKAGE_PATH
from src.schemas import BaseSchema


class CreativeModelConfig(BaseSchema):
    """Configuration for creative model."""

    model_name: str = Field(..., description="The name of the creative LLM to use.")
    temperature: float = Field(0.7, description="The temperature setting for the creative LLM.")
    max_tokens: int = Field(1024, description="The maximum number of tokens for the creative LLM response.")


class StructuredOutputModelConfig(BaseSchema):
    """Configuration for structured output model."""

    model_name: str = Field(..., description="The name of the structured output LLM to use.")
    temperature: float = Field(0.0, description="The temperature setting for the structured output LLM.")
    max_tokens: int = Field(512, description="The maximum number of tokens for the structured output LLM response.")


class LLMModelConfig(BaseSchema):
    """Configuration for models."""

    creative_model: CreativeModelConfig = Field(description="Creative model configuration.")
    structured_output_model: StructuredOutputModelConfig = Field(description="Structured output model configuration.")


class AppConfig(BaseSchema):
    """Application-level configuration."""

    llm_model_config: LLMModelConfig = Field(description="LLM model configurations.")


config_path: Path = PACKAGE_PATH / "src/config/config.yaml"
config: DictConfig = OmegaConf.load(config_path).config
# # Resolve all the variables
resolved_cfg = OmegaConf.to_container(config, resolve=True)
# Validate the config
app_config: AppConfig = AppConfig(**dict(resolved_cfg))  # type: ignore
