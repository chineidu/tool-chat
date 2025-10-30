from typing import Literal

from langchain.messages import RemoveMessage
from langchain_core.messages import (
    AIMessage,
    AnyMessage,
    HumanMessage,
    SystemMessage,
)
from langchain_openai import ChatOpenAI
from langgraph.graph import END

from src import create_logger
from src.config import app_config, app_settings
from src.logic.prompts import (
    no_summary_prompt,
    query_prompt,
    summary_prompt,
    sys_prompt,
)
from src.logic.state import State
from src.logic.tools import date_and_time_tool, search_tool
from src.utilities.model_config import ModelProvider, get_model_name

logger = create_logger(name="nodes")

# ===============================================================
# ========================= CONFIGs =============================
# ===============================================================
MAX_CREATIVE_TOKENS: int = app_config.llm_model_config.creative_model.max_tokens
MAX_SUMMARY_TOKENS: int = app_config.llm_model_config.structured_output_model.max_tokens
MAX_MESSAGES: int = 30

llm_model_name = get_model_name(
    model_provider=app_config.llm_model_config.creative_model.model_provider,
    model_name=app_config.llm_model_config.creative_model.model_name,
)
llm_model_creds = (
    (app_settings.GROQ_API_KEY.get_secret_value(), app_settings.GROQ_URL)
    if llm_model_name == ModelProvider.GROQ
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
    if summarization_llm_name == ModelProvider.GROQ
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
).bind(max_tokens=MAX_CREATIVE_TOKENS)
summarization_llm = ChatOpenAI(
    api_key=summarization_llm_creds[0],  # type: ignore
    base_url=summarization_llm_creds[1],  # type: ignore
    temperature=0.0,
    model=summarization_llm_name,  # type: ignore
).bind(max_tokens=MAX_SUMMARY_TOKENS)


async def llm_call_node(state: State) -> State:
    """Node to call the LLM with tools and conversation history."""
    summary: str = state.get("summary", "")
    sys_msg = SystemMessage(content=sys_prompt)

    if summary:
        summary_msg = SystemMessage(content=f"Summary of conversation:\n\n {summary}")
        # Summary + most recent messages
        msgs_with_summary = [summary_msg] + state["messages"]

    else:
        msgs_with_summary = state["messages"]

    _msg = query_prompt.format(query=state.get("query", ""))
    query = HumanMessage(content=_msg)
    llm_with_tools = llm.bind_tools(tools=[search_tool, date_and_time_tool])
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


# ===============================================================
# =========================== EDGES =============================
# ===============================================================
def should_summarize(state: State) -> Literal["summarize", END]:  # type: ignore
    """Edge to determine if summarization is needed."""
    if len(state["messages"]) > MAX_MESSAGES:
        return "summarize"

    return END
