from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field  # type: ignore
from pydantic.alias_generators import to_camel

from schemas.types import Feedback


def round_probability(value: float) -> float:
    """Round a float value to two decimal places.

    Returns:
    --------
        float: Rounded value.
    """
    if isinstance(value, float):
        return round(value, 2)
    return value


Float = Annotated[float, BeforeValidator(round_probability)]


class BaseSchema(BaseModel):
    """Base schema class that inherits from Pydantic BaseModel.

    This class provides common configuration for all schema classes including
    camelCase alias generation, population by field name, and attribute mapping.
    """

    model_config: ConfigDict = ConfigDict(  # type: ignore
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
        arbitrary_types_allowed=True,
        strict=True,
    )


class FeedbackRequestSchema(BaseModel):
    """Feedback request model."""

    session_id: str = Field(..., description="Session/checkpoint ID")
    message_index: int = Field(..., ge=0, description="Index of the message in conversation")
    user_message: str = Field(default="", description="User's question/prompt")
    assistant_message: str = Field(..., description="Assistant's response")
    sources: list[str] = Field(default_factory=list, description="List of source URLs")
    feedback: Feedback = Field(
        default=Feedback.NEUTRAL,
        description="Feedback type: 'positive', 'negative', or null",
    )
    timestamp: str | None = Field(
        default_factory=lambda: datetime.now().isoformat(timespec="seconds"),
        description="Timestamp (auto-generated if not provided)",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "abc123",
                "message_index": 1,
                "user_message": "What is LangGraph?",
                "assistant_message": "LangGraph is a framework...",
                "sources": ["https://example.com"],
                "feedback": "positive",
            }
        }
