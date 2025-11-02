from typing import Any, Callable
from unittest.mock import MagicMock

from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage, AIMessageChunk

from src.schemas.types import Events


class TestLLMStreaming:
    """Test LLM streaming functionality."""

    def test_content_is_streamed_successfully(
        self,
        client: TestClient,
        parse_sse_event: Callable[[str], list[dict[str, Any]]],
        mock_graph_manager: Callable[[list[dict[str, Any]], Any | None], None],
    ) -> None:
        """Test that content is streamed successfully from the /chat_stream endpoint."""
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

        # Call the endpoint
        with client.stream(
            "GET", "/api/v1/chat_stream", params={"message": "hi"}
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
        parse_sse_event: Callable[[str], list[dict[str, Any]]],
        mock_graph_manager: Callable[[list[dict[str, Any]], Any | None], None],
    ) -> None:
        """Test that content is streamed successfully from the /chat_stream endpoint."""
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

        # Call the endpoint
        with client.stream(
            "GET", "/api/v1/chat_stream", params={"message": "hi"}
        ) as resp:
            content_lines: list[str] = [
                line.decode("utf-8") if isinstance(line, bytes) else line
                for line in resp.iter_lines()
            ]
            raw_content = "\n".join(content_lines)
            received: list[dict[str, Any]] = parse_sse_event(raw_content)

        # Assert
        date_results = [
            e["result"] for e in received if e["type"] == Events.DATE_RESULT
        ]
        assert date_results == ["2023-10-01 12:00:00Z"]
