from src import create_logger
from src.schemas.types import GroqModels, ModelProviders, OpenRouterModels, RemoteModel

logger = create_logger(name="model_config")


MODEL_DICT: dict[ModelProviders, type[RemoteModel]] = {
    ModelProviders.OPENROUTER: OpenRouterModels,
    ModelProviders.GROQ: GroqModels,
}


def get_model_name(
    model_provider: str | ModelProviders, model_name: str | RemoteModel
) -> GroqModels | OpenRouterModels:
    """Returns the model name enum based on the model type and name string."""
    try:
        # Convert string to ModelProviders enum if needed
        if isinstance(model_provider, str):
            provider = ModelProviders(model_provider)
            logger.info(f"Converted model_provider string to enum: {provider}")

        else:
            provider = model_provider
            logger.info(f"Using provided model_provider enum: {provider}")

        model_ = MODEL_DICT[provider]
        return model_(model_name)

    # Default to OpenRouter model if not found
    except (KeyError, ValueError) as e:
        logger.warning(
            f"Model not found for type {model_provider} and name {model_name}: {e}"
        )
        return OpenRouterModels.GEMINI_2_0_FLASH_001  # type: ignore
