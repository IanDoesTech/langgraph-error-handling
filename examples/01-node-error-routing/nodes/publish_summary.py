"""Publishing node for the successful graph path."""

from langchain_core.messages import AIMessage

from state import State


async def publish_summary(state: State) -> dict:
    """Publish the generated summary."""
    return {
        "messages": [AIMessage(content=f"Published: {state['draft']}")],
    }
