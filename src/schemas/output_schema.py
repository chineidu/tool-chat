from uuid import uuid4

from pydantic import Field

from .input_schema import BaseSchema


class FeedbackResponse(BaseSchema):
    """Feedback response model."""

    success: bool
    message: str
    feedback_id: str | None = None


class ChatHistorySchema(BaseSchema):
    """Chat history model."""

    checkpoint_id: str = Field(default_factory=lambda: str(uuid4()), description="Checkpoint ID")
    messages: list[dict[str, str]] = Field(default_factory=list, description="List of chat messages")
    message_count: int = Field(0, description="Total number of messages in the chat history")
