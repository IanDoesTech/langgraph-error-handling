"""Drafting node that demonstrates graph-level error routing."""

from typing import Literal

from langchain_core.messages import AIMessage
from langgraph.types import Command

from examples.node_error_routing.state import State, create_workflow_error

NODE_NAME = "draft_summary"

RouterDestination = Literal["error_handler", "publish_summary"]


async def draft_summary(state: State) -> Command[RouterDestination]:
    """Draft a summary or route failures to the shared error handler."""
    try:
        topic = state["topic"]
        if "fail" in topic.lower():
            raise ValueError("The demo topic intentionally triggered a node failure.")

        return Command(
            goto="publish_summary",
            update={
                "draft": f"Short summary for: {topic}",
                "messages": [AIMessage(content="Drafted the summary.")],
            },
        )
    except Exception as exc:
        print(f"[{NODE_NAME}] failed: {type(exc).__name__}: {exc}")
        return Command(
            goto="error_handler",
            update={
                "error": create_workflow_error(exception=exc, node=NODE_NAME),
            },
        )
