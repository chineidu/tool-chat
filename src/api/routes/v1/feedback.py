"""FastAPI endpoint for handling user feedback."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from src import create_logger
from src.api.core.auth import get_current_active_user
from src.api.core.rate_limit import limiter
from src.db.crud import create_feedback
from src.db.models import get_db
from src.schemas import (
    FeedbackRequestSchema,
    FeedbackResponseSchema,
    UserWithHashSchema,
)
from src.schemas.types import FeedbackType

logger = create_logger(name="feedback_api")


# Create router
router = APIRouter(tags=["feedback"])


@router.post("/feedback", status_code=status.HTTP_200_OK)
@limiter.limit("10/minute")
async def submit_feedback(
    request: Request,  # Required by SlowAPI  # noqa: ARG001
    feedback_data: FeedbackRequestSchema,
    current_user: UserWithHashSchema = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> FeedbackResponseSchema:
    """
    Submit user feedback for a chat message.

    Parameters
    ----------
        feedback_data: Feedback data including session, messages, and rating
        current_user: The authenticated user submitting feedback
        db: Database session

    Returns
    -------
        FeedbackResponse with success status
    """
    try:
        # Set user information from authenticated user
        if not current_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User ID is required",
            )
        feedback_data.user_id = current_user.id
        feedback_data.username = current_user.username

        # Validate feedback type if provided
        if feedback_data.feedback and feedback_data.feedback not in [
            FeedbackType.POSITIVE,
            FeedbackType.NEGATIVE,
            FeedbackType.NEUTRAL,
        ]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Feedback must be {', '.join(fb.value for fb in FeedbackType)}.",
            )

        # Add timestamp if not provided
        if not feedback_data.timestamp:
            feedback_data.timestamp = datetime.now().isoformat()

        # Save feedback to database
        db_feedback = create_feedback(db=db, feedback=feedback_data)

        logger.info(
            f"[FEEDBACK] Session: {feedback_data.session_id}, "
            f"Index: {feedback_data.message_index}, "
            f"Type: {feedback_data.feedback}, "
            f"User: {current_user.username}"
        )

        return FeedbackResponseSchema(
            success=True,
            message="Feedback recorded successfully",
            feedback_id=f"{db_feedback.id}",
            user_id=current_user.id,
            username=current_user.username,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ERROR] Failed to save feedback: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save feedback: {str(e)}",
        ) from e
