from typing import Annotated, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages


class MetaState(TypedDict):
    query: Annotated[list[AnyMessage], add_messages]
    answer: str
    # For storing the entire conversation history. The tools node will also append to this.
    messages: Annotated[list[AnyMessage], add_messages]
    runs: int


class State(MetaState):
    summary: str
