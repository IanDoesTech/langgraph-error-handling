"""State definitions for the node error routing example."""

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
    topic: str
    draft: str | None
    error: WorkflowError | None


def create_workflow_error(*, exception: Exception, node: str) -> WorkflowError:
    """Convert an exception into serializable workflow error state."""
    return {
        "node": node,
        "exception_type": type(exception).__name__,
        "message": str(exception),
    }
