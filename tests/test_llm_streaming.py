"""
Test LLM streaming functionality.
"""

from typing import Any, Callable
from unittest.mock import MagicMock

from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage, AIMessageChunk
from sqlalchemy.orm.session import Session

from src.api.core.auth import create_access_token
from src.db.crud import create_user
from src.schemas import UserWithHashSchema
from src.schemas.types import Events


class TestLLMStreaming:
    """Test LLM streaming functionality."""

    def test_content_is_streamed_successfully(
        self,
        client: TestClient,
        db_session: Session,
        parse_sse_event: Callable[[str], list[dict[str, Any]]],
        mock_graph_manager: Callable[[list[dict[str, Any]], Any | None], None],
    ) -> None:
        """Test that content is streamed successfully from the /chat_stream endpoint."""
        # Create a test user in the database
        test_user = UserWithHashSchema(
            id=1,
            username="testuser",
            firstname="Test",
            lastname="User",
            email="test@example.com",
            hashed_password="hashed",
            is_active=True,
            roles=["user"],
        )
        create_user(db=db_session, user=test_user)

        # Create a JWT token for authentication
        token = create_access_token({"sub": "testuser"})

        events: list[dict[str, Any]] = [
            {
                "event": "on_chat_model_stream",
                "data": {"chunk": AIMessageChunk(content="Hello")},
                "metadata": {"langgraph_node": "llm_call"},
            },
            {
                "event": "on_chat_model_end",
                "data": {"output": MagicMock(tool_calls=[])},
            },
        ]
        mock_graph_manager(events, client.app)

        # Call the endpoint with authentication
        headers = {"Authorization": f"Bearer {token}"}
        with client.stream(
            "GET", "/api/v1/chat_stream", params={"message": "hi"}, headers=headers
        ) as resp:
            content_lines = [
                line.decode("utf-8") if isinstance(line, bytes) else line
                for line in resp.iter_lines()
            ]
            raw_content = "\n".join(content_lines)
            received = parse_sse_event(raw_content)

        # Assert
        content = [e["content"] for e in received if e["type"] == Events.CONTENT]
        assert content == ["Hello"]

    def test_tool_call_successfully(
        self,
        client: TestClient,
        db_session: Session,
        parse_sse_event: Callable[[str], list[dict[str, Any]]],
        mock_graph_manager: Callable[[list[dict[str, Any]], Any | None], None],
    ) -> None:
        """Test that tool calls are handled successfully from the /chat_stream endpoint."""
        # Create a test user in the database
        test_user = UserWithHashSchema(
            id=1,
            username="testuser",
            firstname="Test",
            lastname="User",
            email="test@example.com",
            hashed_password="hashed",
            is_active=True,
            roles=["user"],
        )
        create_user(db=db_session, user=test_user)

        # Create a JWT token for authentication
        token = create_access_token({"sub": "testuser"})

        events: list[dict[str, Any]] = [
            {
                "event": "on_chat_model_end",
                "data": {
                    "output": AIMessage(
                        content="",
                        additional_kwargs={},
                        response_metadata={
                            "finish_reason": "tool_calls",
                            "model_name": "google/gemini-2.0-flash-001",
                            "model_provider": "openai",
                        },
                        id="lc_run--bc4e517b-2775-4f83-8eae-84f532d1b235",
                        tool_calls=[
                            {
                                "name": "date_and_time_tool",
                                "args": {},
                                "id": "tool_0_date_and_time_tool_VThszOTJjVBiIUPQia13",
                                "type": "tool_call",
                            }
                        ],
                    )
                },
                "metadata": {"langgraph_node": "llm_call"},
            },
            {
                "event": "on_tool_end",
                "name": "date_and_time_tool",
                "data": {
                    "output": AIMessage(
                        content="2023-10-01T12:00:00Z",
                        name="date_and_time_tool",
                        tool_call_id="tool_0_date_and_time_tool_VThszOTJjVBiIUPQia13",
                    )
                },
            },
        ]
        mock_graph_manager(events, client.app)

        # Call the endpoint with authentication
        headers = {"Authorization": f"Bearer {token}"}
        with client.stream(
            "GET", "/api/v1/chat_stream", params={"message": "hi"}, headers=headers
        ) as resp:
            print(f"Response status: {resp.status_code}")
            if resp.status_code != 200:
                print(f"Response text: {resp.text}")
            content_lines: list[str] = [
                line.decode("utf-8") if isinstance(line, bytes) else line
                for line in resp.iter_lines()
            ]
            raw_content = "\n".join(content_lines)
            print(f"Raw content: {raw_content}")
            received: list[dict[str, Any]] = parse_sse_event(raw_content)

        # Assert
        date_results = [
            e["result"] for e in received if e["type"] == Events.DATE_RESULT
        ]
        assert date_results == ["2023-10-01 12:00:00Z"]
