"""User-facing error handler for exhausted child-subgraph retries."""

import logging

from langchain_core.messages import AIMessage

from examples.subgraph_retry_policy.state import State

logger = logging.getLogger(__name__)

ERROR_MESSAGE = (
    "Sorry, documentation search failed after retries. "
    "The issue has been reported to support."
)


async def error_handler(state: State) -> dict:
    """Report the child graph failure to the user and clear the workflow error."""
    logger.info("[error_handler] handled error: %s", state["error"])
    return {
        "messages": [AIMessage(content=ERROR_MESSAGE)],
        "error": None,
    }
