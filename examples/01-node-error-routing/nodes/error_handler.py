"""User-facing error handler for graph failures."""

from langchain_core.messages import AIMessage

from state import State

ERROR_MESSAGE = (
    "Sorry, something went wrong while drafting the summary. "
    "The issue has been reported to support."
)


async def error_handler(state: State) -> dict:
    """Report a friendly failure message and clear the workflow error."""
    print(f"[error_handler] handled error: {state['error']}")
    return {
        "messages": [AIMessage(content=ERROR_MESSAGE)],
        "error": None,
    }
