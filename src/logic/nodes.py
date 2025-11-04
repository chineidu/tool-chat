from typing import Literal

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
from src.utilities.model_config import ModelProviders, get_model_name

logger = create_logger(name="nodes")

# ===============================================================
# ========================= CONFIGs =============================
# ===============================================================
MAX_CREATIVE_TOKENS: int = app_config.llm_model_config.creative_model.max_tokens
MAX_SUMMARY_TOKENS: int = app_config.llm_model_config.structured_output_model.max_tokens
MAX_MESSAGES: int = 40

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
    model=llm_model_name,  # type: ignore
)
summarization_llm = ChatOpenAI(
    api_key=summarization_llm_creds[0],  # type: ignore
    base_url=summarization_llm_creds[1],  # type: ignore
    temperature=0.0,
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

    _msg = query_prompt.format(query=state.get("query", ""))
    query = HumanMessage(content=_msg)
    llm_with_tools = llm.bind_tools(
        tools=[search_tool, date_and_time_tool],
    ).bind(max_tokens=MAX_CREATIVE_TOKENS)
    response = await llm_with_tools.ainvoke([sys_msg] + msgs_with_summary + [query])

    return State(
        query=state.get("query", ""),
        answer=response.content,  # type: ignore
        messages=[state.get("query", ""), response],  # type: ignore
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

    response: AIMessage = await summarization_llm.ainvoke(
        state["messages"] + summary_msg
    )
    logger.info("Conversation history summarized.")

    # Delete ALL but the last 2 messages
    messages_to_remove = [RemoveMessage(id=m.id) for m in state["messages"][:-2]]  # type: ignore

    return State(
        query=state.get("query", None),  # type: ignore
        answer=state.get("answer", None),  # type: ignore
        messages=messages_to_remove,  # type: ignore
        summary=response.content,  # type: ignore
    )


async def update_memory(
    state: State, config: RunnableConfig, store: BaseStore
) -> State:
    """Update user memory based on the conversation."""
    user_id: str = config["configurable"]["user_id"]

    # Retrieve existing memory from the store
    namespace: tuple[str, str] = ("memory", user_id)
    key: str = "user_details"
    user_details = await store.aget(namespace, key)

    # Extract memory if it exists
    if user_details:
        user_details_content = user_details.value.get("memory")
    else:
        user_details_content = "No memory found."

    sys_msg = update_user_memory_prompt.format(
        user_details_content=user_details_content
    )

    # Call the LLM to update memory
    new_memory = await llm.ainvoke([SystemMessage(content=sys_msg)] + state["messages"])

    # If new memory is provided, update the store
    if new_memory.content.strip():  # type: ignore
        await store.aput(namespace, key, value={"memory": new_memory.content})

    return State(
        messages=state["messages"],
        query=state["query"],
        answer=state["answer"],
        summary=state["summary"],
    )


# ===============================================================
# =========================== EDGES =============================
# ===============================================================
def should_summarize(state: State) -> Literal["summarize", END]:  # type: ignore
    """Edge to determine if summarization is needed."""
    if len(state["messages"]) > MAX_MESSAGES:
        return "summarize"

    return END
