"""FastAPI endpoint for handling user feedback."""

from datetime import datetime

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from src import create_logger
from src.schemas import FeedbackRequestSchema
from src.schemas.types import Feedback

logger = create_logger(name="feedback_api")


class FeedbackResponse(BaseModel):
    """Feedback response model."""

    success: bool
    message: str
    feedback_id: str | None = None


# Create router
router = APIRouter(tags=["feedback"])


@router.post("/feedback", status_code=status.HTTP_200_OK)
async def submit_feedback(feedback_data: FeedbackRequestSchema) -> FeedbackResponse:
    """
    Submit user feedback for a chat message.

    Args:
        feedback_data: Feedback data including session, messages, and rating

    Returns:
        FeedbackResponse with success status
    """
    try:
        # Validate feedback type if provided
        if feedback_data.feedback and feedback_data.feedback not in [
            Feedback.POSITIVE,
            Feedback.NEGATIVE,
            Feedback.NEUTRAL,
        ]:
            raise HTTPException(
                status_code=400,
                detail="Feedback must be 'positive', 'negative', or null",
            )

        # Add timestamp if not provided
        if not feedback_data.timestamp:
            feedback_data.timestamp = datetime.now().isoformat()

        # Here you would typically save to a database

        # For now, log to console/file
        import json

        feedback_log_path = "feedback_logs.jsonl"

        log_entry = {
            "session_id": feedback_data.session_id,
            "message_index": feedback_data.message_index,
            "user_message": feedback_data.user_message,
            "assistant_message": feedback_data.assistant_message,
            "sources": feedback_data.sources,
            "feedback": feedback_data.feedback,
            "timestamp": feedback_data.timestamp,
        }

        # Append to JSONL file
        with open(feedback_log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry) + "\n")

        logger.info(
            f"[FEEDBACK] Session: {feedback_data.session_id}, "
            f"Index: {feedback_data.message_index}, "
            f"Type: {feedback_data.feedback}"
        )

        return FeedbackResponse(
            success=True,
            message="Feedback recorded successfully",
            feedback_id=f"{feedback_data.session_id}_{feedback_data.message_index}",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ERROR] Failed to save feedback: {str(e)}")
        import traceback

        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save feedback: {str(e)}",
        ) from e
