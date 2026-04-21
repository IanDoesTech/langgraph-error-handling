"""User-facing error handler for exhausted child-subgraph retries."""

from langchain_core.messages import AIMessage

from examples.subgraph_retry_policy.state import State

ERROR_MESSAGE = (
    "Sorry, documentation search failed after retries. "
    "The issue has been reported to support."
)


async def error_handler(state: State) -> dict:
    """Report the child graph failure to the user and clear the workflow error."""
    print(f"[error_handler] handled error: {state['error']}")
    return {
        "messages": [AIMessage(content=ERROR_MESSAGE)],
        "error": None,
    }
