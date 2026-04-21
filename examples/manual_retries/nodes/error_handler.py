"""User-facing error handler for exhausted manual retries."""

from langchain_core.messages import AIMessage

from examples.manual_retries.state import State

ERROR_MESSAGE = (
    "Sorry, documentation search is temporarily unavailable. "
    "The issue has been reported to support."
)


async def error_handler(state: State) -> dict:
    """Report retry exhaustion to the user and clear the workflow error."""
    print(f"[error_handler] handled error: {state['error']}")
    return {
        "messages": [AIMessage(content=ERROR_MESSAGE)],
        "error": None,
    }
