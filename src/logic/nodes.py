from typing import Any, Literal

from langchain.messages import RemoveMessage
from langchain_core.messages import (
    AIMessage,
    AnyMessage,
    HumanMessage,
    SystemMessage,
)
from langchain_core.runnables.config import RunnableConfig
from langchain_openai import ChatOpenAI
from langgraph.graph import END
from langgraph.store.base import BaseStore

from src import create_logger
from src.config import app_config, app_settings
from src.logic.prompts import (
    no_summary_prompt,
    query_prompt,
    summary_prompt,
    sys_prompt,
    update_user_memory_prompt,
)
from src.logic.state import State
from src.logic.tools import date_and_time_tool, search_tool
from src.logic.utils import (
    append_memory,
    convert_langchain_messages_to_dicts,
    get_structured_output,
)
from src.schemas import StructuredMemoryResponse
from src.schemas.types import OpenRouterModels
from src.utilities.model_config import ModelProviders, get_model_name

logger = create_logger(name="nodes")

# ===============================================================
# ========================= CONFIGs =============================
# ===============================================================
MAX_CREATIVE_TOKENS: int = app_config.llm_model_config.creative_model.max_tokens
MAX_SUMMARY_TOKENS: int = app_config.llm_model_config.structured_output_model.max_tokens
MAX_MESSAGES: int = 10  # 20

llm_model_name = get_model_name(
    model_provider=app_config.llm_model_config.creative_model.model_provider,
    model_name=app_config.llm_model_config.creative_model.model_name,
)
llm_model_creds = (
    (app_settings.GROQ_API_KEY.get_secret_value(), app_settings.GROQ_URL)
    if llm_model_name == ModelProviders.GROQ
    else (
        app_settings.OPENROUTER_API_KEY.get_secret_value(),
        app_settings.OPENROUTER_URL,
    )
)
summarization_llm_name = get_model_name(
    model_provider=app_config.llm_model_config.structured_output_model.model_provider,
    model_name=app_config.llm_model_config.structured_output_model.model_name,
)
summarization_llm_creds = (
    (app_settings.GROQ_API_KEY.get_secret_value(), app_settings.GROQ_URL)
    if summarization_llm_name == ModelProviders.GROQ
    else (
        app_settings.OPENROUTER_API_KEY.get_secret_value(),
        app_settings.OPENROUTER_URL,
    )
)

llm = ChatOpenAI(
    api_key=llm_model_creds[0],  # type: ignore
    base_url=llm_model_creds[1],  # type: ignore
    temperature=0.0,
    seed=1,
    model=llm_model_name,  # type: ignore
)
summarization_llm = ChatOpenAI(
    api_key=summarization_llm_creds[0],  # type: ignore
    base_url=summarization_llm_creds[1],  # type: ignore
    temperature=0.0,
    seed=1,
    model=summarization_llm_name,  # type: ignore
).bind(max_tokens=MAX_SUMMARY_TOKENS)


async def llm_call_node(
    state: State, config: RunnableConfig, store: BaseStore
) -> State:  # noqa: ARG001
    """Node to call the LLM with tools and conversation history."""
    summary: str = state.get("summary", "")

    # ========================================================
    # ============== Process Long-term Memory ================
    # ========================================================
    user_id: str = config["configurable"]["user_id"]

    # Retrieve memory from the store
    namespace: tuple[str, str] = ("memory", user_id)
    key: str = "user_details"
    user_details = await store.aget(namespace, key)

    # Extract memory if it exists
    if user_details:
        user_details_content = user_details.value.get("memory")
    else:
        user_details_content = "No memory found."

    sys_msg_prompt: str = sys_prompt.format(user_details_content=user_details_content)
    sys_msg = SystemMessage(content=sys_msg_prompt)

    if summary:
        summary_msg = SystemMessage(content=f"Summary of conversation:\n\n {summary}")
        # Summary + most recent messages
        msgs_with_summary: list[AnyMessage] = [summary_msg] + state["messages"]

    else:
        msgs_with_summary = state["messages"]

    _query: str = state.get("query", "")[-1] if state.get("query", "") else ""
    _msg = query_prompt.format(query=_query)
    query = HumanMessage(content=_msg)
    inputs = [sys_msg] + msgs_with_summary + [query]
    try:
        llm_with_tools = llm.bind_tools(tools=[search_tool, date_and_time_tool]).bind(
            max_tokens=MAX_CREATIVE_TOKENS
        )
        response = await llm_with_tools.ainvoke(inputs)

    except Exception as e:
        logger.error(f"⚠️ Error in LLM call with tools: {e}")
        # Fallback to LLM without tools if tool calling fails
        llm_fallback = llm.bind(max_tokens=MAX_CREATIVE_TOKENS)
        response = await llm_fallback.ainvoke(inputs)

    return State(
        query=state.get("query", []),
        answer=response.content,  # type: ignore
        # Append the latest user query and LLM response to messages
        # It will be added to the conversation history using the `add_messages` reducer
        messages=[state.get("query", "")[-1] if state.get("query", "") else ""]
        + [response],  # type: ignore
        runs=state.get("runs", 0),
        summary=summary,
    )


async def summarization_node(state: State) -> State:
    """Summarization node to condense the conversation history."""
    summary: str = state.get("summary", "")

    if summary:
        summary_msg: list[AnyMessage] = [
            HumanMessage(content=summary_prompt.format(summary=summary))
        ]
    else:
        summary_msg = [HumanMessage(content=no_summary_prompt)]

    try:
        response: AIMessage = await summarization_llm.ainvoke(
            state["messages"] + summary_msg
        )
        logger.info("✅ Conversation history summarized.")

    except Exception as e:
        logger.warning(f"⚠️ Error in summarization LLM call: {e}")
        # Fallback to returning the existing summary if summarization fails
        return State(
            query=state.get("query", []),  # type: ignore
            answer=state.get("answer", None),  # type: ignore
            messages=[],  # type: ignore
            runs=state.get("runs", 0),
            summary=summary,
        )

    # Delete ALL but the last 2 messages
    messages_to_remove = [RemoveMessage(id=m.id) for m in state["messages"][:-2]]  # type: ignore

    return State(
        query=state.get("query", []),  # type: ignore
        answer=state.get("answer", None),  # type: ignore
        # The `add_messages` reducer will handle removing the old messages
        messages=messages_to_remove,  # type: ignore
        runs=state.get("runs", 0),
        summary=response.content,  # type: ignore
    )


async def update_memory_node(
    state: State, config: RunnableConfig, store: BaseStore
) -> None:
    """Update user memory based on the conversation."""
    try:
        user_id: str = config["configurable"]["user_id"]
        namespace: tuple[str, str] = ("memory", user_id)
        key: str = "user_details"

        # Get existing memory
        user_details = await store.aget(namespace, key)
        existing_memory = user_details.value.get("memory", {}) if user_details else {}

        # Format for prompt (convert dict to readable string)
        if existing_memory:
            formatted: str = "\n".join(
                f"- {k}: {v}" for k, v in existing_memory.items() if v
            )
        else:
            formatted = "No memory found."

        sys_msg: str = update_user_memory_prompt.format(user_details_content=formatted)
        summary: str = state.get("summary", "")

        # Build context
        context = [SystemMessage(content=sys_msg)]
        if summary:
            context.append(SystemMessage(content=f"Summary: {summary}"))
        # Add recent messages
        context.extend(state["messages"])

        try:
            messages: list[dict[str, str]] = convert_langchain_messages_to_dicts(
                context
            )
            new_memory: StructuredMemoryResponse = await get_structured_output(  # type: ignore
                messages=messages,
                model=OpenRouterModels.LLAMA_3_3_70B_INSTRUCT,
                schema=StructuredMemoryResponse,
            )
        except Exception as e:
            logger.warning(f"⚠️ Error in memory update: {e}")
            return

        if new_memory:
            # Simple append: existing + new
            updated_memory: dict[str, Any] = append_memory(
                existing_memory, new_memory.model_dump()
            )

            await store.aput(namespace, key, value={"memory": updated_memory})
            logger.info("💥 Memory updated")

    except Exception as e:
        logger.warning(f"⚠️ Error in update_memory_node: {e}")

    return


# ===============================================================
# =========================== EDGES =============================
# ===============================================================
def should_summarize(state: State) -> Literal["summarize", END]:  # type: ignore
    """Edge to determine if summarization is needed."""
    if len(state["messages"]) > MAX_MESSAGES:
        return "summarize"

    return END


def should_continue_tools(state: State) -> Literal["tools", END]:  # type: ignore
    """Edge to determine if tool calling is needed."""
    pass
