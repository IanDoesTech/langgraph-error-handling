"""Response node for the parent graph's successful path."""

from langchain_core.messages import AIMessage

from examples.subgraph_retry_policy.state import State


async def answer_user(state: State) -> dict:
    """Return the retried subgraph result to the user."""
    return {
        "messages": [AIMessage(content=state["result"] or "No result was found.")],
    }
