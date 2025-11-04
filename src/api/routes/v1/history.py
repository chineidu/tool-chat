from typing import Any

from aiocache import Cache
from fastapi import APIRouter, Depends, HTTPException, Request, status
from langchain_core.messages import BaseMessage

from src import create_logger
from src.api import get_cache, get_graph_manager
from src.api.core.cache import cached
from src.api.core.rate_limit import limiter
from src.logic.graph import GraphManager
from src.schemas import ChatHistorySchema

logger = create_logger(name="status_route")

router = APIRouter(tags=["history"])


@router.get("/chat_history", status_code=status.HTTP_200_OK)
@limiter.limit("30/minute")
@cached(ttl=600, key_prefix="chat_history")  # type: ignore
async def get_chat_history(
    request: Request,  # Required by SlowAPI  # noqa: ARG001
    checkpoint_id: str,
    graph_manager: GraphManager = Depends(get_graph_manager),
    cache: Cache = Depends(get_cache),  # noqa: ARG001
) -> ChatHistorySchema:
    """
    Retrieve the conversation history for a given checkpoint ID.

    Parameters
    ----------
    checkpoint_id:
        The checkpoint ID to retrieve history for

    Returns
    -------
    ChatHistorySchema
        The chat history including messages and message count
    """
    try:
        config: dict[str, Any] = {"configurable": {"thread_id": checkpoint_id}}
        graph = await graph_manager.build_graph()

        # Get the state from the checkpoint
        state = await graph.aget_state(config)  # type: ignore

        if not state or not state.values or not state.values.get("messages"):
            logger.error(f"Checkpoint '{checkpoint_id}' not found or has no messages")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Checkpoint '{checkpoint_id}' not found or has no messages",
            )

        # Extract messages from state
        messages: list[BaseMessage] = state.values.get("messages", [])

        # Convert messages to a serializable format
        formatted_messages: list[dict[str, str]] = []
        for msg in messages:
            if hasattr(msg, "type"):
                msg_type = msg.type
            else:
                msg_type = msg.__class__.__name__.replace("Message", "").lower()

            formatted_messages.append({"role": msg_type, "content": msg.content})  # type: ignore

        logger.info(
            f"Retrieved {len(formatted_messages)} messages from checkpoint '{checkpoint_id}'"
        )

        return ChatHistorySchema(
            **{  # type: ignore
                "checkpoint_id": checkpoint_id,
                "messages": formatted_messages,
                "message_count": len(formatted_messages),
            }
        ).model_dump()

    except HTTPException:
        logger.error("HTTP error occurred")
        raise
    except Exception as e:
        logger.error(f"Unexpected error occurred: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error retrieving checkpoint: {str(e)}"
        ) from e
