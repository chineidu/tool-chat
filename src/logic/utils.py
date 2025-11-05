from typing import Any

import instructor
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from openai import AsyncOpenAI

from src.config import app_settings
from src.schemas.types import OpenRouterModels, PydanticModel

_async_client = AsyncOpenAI(
    api_key=app_settings.OPENROUTER_API_KEY.get_secret_value(),
    base_url=app_settings.OPENROUTER_URL,
)

aclient = instructor.from_openai(
    _async_client,
    mode=instructor.Mode.OPENROUTER_STRUCTURED_OUTPUTS,
)


async def get_structured_output(
    messages: list[dict[str, Any]],
    model: OpenRouterModels | None,
    schema: PydanticModel,
) -> PydanticModel:
    """
    Retrieves structured output from a chat completion model.

    Parameters
    ----------
    messages : list[dict[str, Any]]
        The list of messages to send to the model for the chat completion.
    model : RemoteModel
        The remote model to use for the chat completion (e.g., 'gpt-4o').
    schema : PydanticModel
        The Pydantic schema to enforce for the structured output.

    Returns
    -------
    BaseModel
        An instance of the provided Pydantic schema containing the structured output.

    Notes
    -----
    This is an asynchronous function that awaits the completion of the API call.
    """
    model = model if model else OpenRouterModels.GEMINI_2_0_FLASH_LITE

    return await aclient.chat.completions.create(
        model=model,
        response_model=schema,
        messages=messages,  # type: ignore
        max_retries=5,
    )


def convert_langchain_messages_to_dicts(
    messages: list[HumanMessage | SystemMessage | AIMessage],
) -> list[dict[str, str]]:
    """Convert LangChain messages to a list of dictionaries.

    Parameters
    ----------
    messages : list[HumanMessage | SystemMessage | AIMessage]
        List of LangChain message objects to convert.

    Returns
    -------
    list[dict[str, str]]
        List of dictionaries with 'role' and 'content' keys.
        Roles are mapped as follows:
        - HumanMessage -> "user"
        - SystemMessage -> "system"
        - AIMessage -> "assistant"

    """
    role_mapping: dict[str, str] = {
        "SystemMessage": "system",
        "HumanMessage": "user",
        "AIMessage": "assistant",
    }

    converted_messages: list[dict[str, str]] = []
    for msg in messages:
        message_type: str = msg.__class__.__name__
        # Default to "user" if unknown
        role: str = role_mapping.get(message_type, "user")
        converted_messages.append({"role": role, "content": msg.content})  # type: ignore

    return converted_messages


def append_memory(existing: dict[str, Any], new: dict[str, Any]) -> dict[str, Any]:
    """Merge new memory data into existing memory, appending lists and merging dicts.

    Parameters
    ----------
    existing: dict[str, Any]
        The existing memory data.
    new: dict[str, Any]
        The new memory data to merge.

    Returns
    -------
    dict[str, Any]
        The merged memory data.
    """
    result: dict[str, Any] = existing.copy()

    for key, new_value in new.items():
        # Skip None or empty values
        if new_value is None or new_value == "" or new_value == []:
            continue

        existing_value = result.get(key)

        # If key doesn't exist, just add it
        if existing_value is None:
            result[key] = new_value
            continue

        # Lists: combine and remove duplicates
        if isinstance(new_value, list):
            combined = existing_value + new_value
            # Preserve order, remove duplicates
            # ["a", "b", "a"] -> ["a", "b"]
            result[key] = list(dict.fromkeys(combined))

        # Dicts: merge
        elif isinstance(new_value, dict):
            result[key] = {**existing_value, **new_value}

        # Everything else: new value overwrites
        else:
            result[key] = new_value

    return result
