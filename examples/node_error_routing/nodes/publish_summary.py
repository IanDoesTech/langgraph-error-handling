"""Publishing node for the successful graph path."""

from langchain_core.messages import AIMessage

from examples.node_error_routing.state import State


async def publish_summary(state: State) -> dict:
    """Publish the generated summary."""
    return {
        "messages": [AIMessage(content=f"Published: {state['draft']}")],
    }
