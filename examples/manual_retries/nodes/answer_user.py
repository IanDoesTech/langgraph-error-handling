"""Response node for the successful manual retry path."""

from langchain_core.messages import AIMessage

from examples.manual_retries.state import State


async def answer_user(state: State) -> dict:
    """Return the search result to the user."""
    return {
        "messages": [AIMessage(content=state["result"] or "No result was found.")],
    }
