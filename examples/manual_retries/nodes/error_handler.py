"""User-facing error handler for exhausted manual retries."""

import logging

from langchain_core.messages import AIMessage

from examples.manual_retries.state import State

logger = logging.getLogger(__name__)

ERROR_MESSAGE = (
    "Sorry, something went wrong while processing your latest submission. "
    "The issue has been reported to support."
)


async def error_handler(state: State) -> dict:
    """Report retry exhaustion to the user and clear the workflow error."""
    logger.info("[error_handler] handled error: %s", state["error"])
    return {
        "messages": [AIMessage(content=ERROR_MESSAGE)],
        "error": None,
    }
