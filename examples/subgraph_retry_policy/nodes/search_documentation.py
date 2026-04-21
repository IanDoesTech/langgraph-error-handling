"""Child-subgraph node that raises retryable transient failures."""

import os

from dotenv import load_dotenv

from examples.subgraph_retry_policy.state import SearchState

load_dotenv()


class TemporarySearchError(Exception):
    """Retryable exception used by the child graph's RetryPolicy."""


attempt_counter = 0


async def search_documentation(state: SearchState) -> dict:
    """Search documentation and raise so LangGraph can apply RetryPolicy."""
    global attempt_counter
    attempt_counter += 1

    fail_first_n_attempts = int(os.getenv("FAIL_FIRST_N_ATTEMPTS", "2"))
    if attempt_counter <= fail_first_n_attempts:
        print(f"[retried_subgraph] attempt {attempt_counter} failed")
        raise TemporarySearchError(
            f"simulated transient failure for attempt {attempt_counter}"
        )

    return {
        "result": f"Found documentation result for: {state['query']}",
    }


def reset_attempt_counter() -> None:
    """Reset the fake service counter before a parent graph invocation."""
    global attempt_counter
    attempt_counter = 0
