from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.types import RetryPolicy

from src import create_logger
from src.config import app_settings
from src.logic.nodes import llm_call_node, should_summarize, summarization_node
from src.logic.state import State
from src.logic.tools import date_and_time_tool, search_tool

logger = create_logger(name="graph_manager")

MAX_ATTEMPTS: int = 3
DB_URI = (
    f"postgresql://{app_settings.POSTGRES_USER}:"
    f"{app_settings.POSTGRES_PASSWORD.get_secret_value()}@{app_settings.POSTGRES_HOST}:"
    f"{app_settings.POSTGRES_PORT}/{app_settings.POSTGRES_DB}?sslmode=disable"
)


class GraphManager:
    """Manages LangGraph instances with PostgreSQL checkpointing."""

    def __init__(self) -> None:
        self.checkpointer: AsyncPostgresSaver | None = None
        self.checkpointer_context = None
        self.graph_instance: CompiledStateGraph | None = None

    async def initialize_checkpointer(self) -> None:
        """Initialize the Postgres checkpointer."""
        if self.checkpointer is None:
            self.checkpointer_context = AsyncPostgresSaver.from_conn_string(DB_URI)
            self.checkpointer = await self.checkpointer_context.__aenter__()  # type: ignore
            await self.checkpointer.setup()

    async def cleanup_checkpointer(self) -> None:
        """Clean up the Postgres checkpointer."""
        if self.checkpointer_context is not None and self.checkpointer is not None:
            try:
                await self.checkpointer_context.__aexit__(None, None, None)
            except Exception as e:
                logger.error(f"Error cleaning up checkpointer: {e}")
            finally:
                self.checkpointer = None
                self.checkpointer_context = None

    async def build_graph(self) -> CompiledStateGraph:
        """
        Build and compile the state graph. This asynchronous method constructs a
        StateGraph with predefined nodes and edges.

        Returns
        -------
        CompiledStateGraph
            The compiled state graph ready for execution, equipped with checkpointer
            for persistence across sessions.
        """
        # Return cached instance if it exists
        if self.graph_instance is not None:
            return self.graph_instance

        # Ensure checkpointer is initialized
        if self.checkpointer is None:
            await self.initialize_checkpointer()

        builder: StateGraph = StateGraph(State)

        # Add nodes
        tool_node = ToolNode([date_and_time_tool, search_tool])

        builder.add_node(
            "llm_call",
            llm_call_node,
            retry_policy=RetryPolicy(max_attempts=MAX_ATTEMPTS, initial_interval=1.0),
        )
        builder.add_node(
            "tools",
            tool_node,
            retry_policy=RetryPolicy(max_attempts=MAX_ATTEMPTS, initial_interval=1.0),
        )
        builder.add_node(
            "summarize",
            summarization_node,
            retry_policy=RetryPolicy(max_attempts=MAX_ATTEMPTS, initial_interval=1.0),
        )

        # Add edges
        builder.add_edge(START, "llm_call")
        builder.add_conditional_edges(
            "llm_call", tools_condition, {"tools": "tools", END: END}
        )
        builder.add_conditional_edges(
            "llm_call", should_summarize, {"summarize": "summarize", END: END}
        )
        builder.add_edge("tools", "llm_call")

        # Compile the graph with persistent Postgres checkpointer
        self.graph_instance = builder.compile(checkpointer=self.checkpointer)
        logger.info("Graph instance built and compiled with Postgres checkpointer.")

        return self.graph_instance
