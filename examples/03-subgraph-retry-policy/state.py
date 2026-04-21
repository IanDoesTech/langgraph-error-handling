"""State definitions for the subgraph retry policy example."""

from typing import Annotated
from typing_extensions import TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages


class WorkflowError(TypedDict):
    node: str
    exception_type: str
    message: str


class State(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    query: str
    result: str | None
    error: WorkflowError | None


class SearchState(TypedDict):
    query: str
    result: str | None


def create_workflow_error(*, exception: Exception, node: str) -> WorkflowError:
    """Convert an exception into serializable workflow error state."""
    return {
        "node": node,
        "exception_type": type(exception).__name__,
        "message": str(exception),
    }
