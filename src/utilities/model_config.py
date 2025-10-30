from src import create_logger
from src.schemas.types import GroqModels, ModelProvider, OpenRouterModels, RemoteModel

logger = create_logger(name="model_config")


MODEL_DICT: dict[ModelProvider, type[RemoteModel]] = {
    ModelProvider.OPENROUTER: OpenRouterModels,
    ModelProvider.GROQ: GroqModels,
}


def get_model_name(
    model_provider: str | ModelProvider, model_name: str | RemoteModel
) -> GroqModels | OpenRouterModels:
    """Returns the model name enum based on the model type and name string."""
    try:
        # Convert string to ModelProvider enum if needed
        if isinstance(model_provider, str):
            provider = ModelProvider(model_provider)
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
        return OpenRouterModels.GEMINI_2_0_FLASH_001
