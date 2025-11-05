from uuid import uuid4

from pydantic import BaseModel, Field

from .input_schema import BaseSchema


class FeedbackResponseSchema(BaseSchema):
    """Feedback response model."""

    success: bool
    message: str
    feedback_id: str | None = None
    user_id: int | None = None
    username: str | None = None


class ChatHistorySchema(BaseSchema):
    """Chat history model."""

    checkpoint_id: str = Field(
        default_factory=lambda: str(uuid4()), description="Checkpoint ID"
    )
    messages: list[dict[str, str]] = Field(
        default_factory=list, description="List of chat messages"
    )
    message_count: int = Field(
        0, description="Total number of messages in the chat history"
    )


class HealthStatusSchema(BaseSchema):
    """Health status model."""

    status: str = Field(..., description="Current status of the API")
    version: str = Field(..., description="API version")


class StructuredMemoryResponse(BaseModel):
    """Schema for structured memory response."""

    # Personal Identity
    name: list[str] = Field(
        default_factory=list, description="User's full name or preferred name"
    )
    location: list[str] = Field(
        default_factory=list,
        description="User's current location (city, country, or region)",
    )
    # Professional Context
    occupation: list[str] = Field(
        default_factory=list, description="User's job title, role, or profession"
    )
    # Personal Interests
    interests: list[str] = Field(
        default_factory=list,
        description="User's hobbies, interests, and activities they enjoy",
    )
    # Additional Context
    pain_points: list[str] = Field(
        default_factory=list,
        description="Challenges, pain points, or recurring issues the user faces",
    )
    other_details: list[str] = Field(
        default_factory=list,
        description="Any other relevant user details that don't fit other categories",
    )
