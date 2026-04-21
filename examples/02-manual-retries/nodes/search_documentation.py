"""Search node that implements retries directly in application code."""

import os
from typing import Literal

from dotenv import load_dotenv
from langchain_core.messages import AIMessage
from langgraph.types import Command

from retry import retry_async
from state import State, create_workflow_error

load_dotenv()

NODE_NAME = "search_documentation"
MAX_ATTEMPTS = 3

RouterDestination = Literal["error_handler", "answer_user"]


class TemporarySearchError(Exception):
    """Retryable exception raised by the fake documentation service."""


async def flaky_documentation_search(query: str, attempt: int) -> str:
    """Simulate a documentation search that fails for the first few attempts."""
    fail_first_n_attempts = int(os.getenv("FAIL_FIRST_N_ATTEMPTS", "2"))
    if attempt <= fail_first_n_attempts:
        raise TemporarySearchError(f"simulated transient failure for attempt {attempt}")
    return f"Found documentation result for: {query}"


async def search_documentation(state: State) -> Command[RouterDestination]:
    """Search documentation with manual retries, then route success or failure."""
    try:
        result, attempts = await retry_async(
            lambda attempt: flaky_documentation_search(state["query"], attempt),
            max_attempts=MAX_ATTEMPTS,
            retry_exceptions=(TemporarySearchError,),
        )
        return Command(
            goto="answer_user",
            update={
                "attempts": attempts,
                "result": result,
                "messages": [AIMessage(content=f"Search succeeded after {attempts} attempt(s).")],
            },
        )
    except Exception as exc:
        print(f"[{NODE_NAME}] retries exhausted: {type(exc).__name__}: {exc}")
        return Command(
            goto="error_handler",
            update={
                "attempts": MAX_ATTEMPTS,
                "error": create_workflow_error(exception=exc, node=NODE_NAME),
            },
        )
