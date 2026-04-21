"""Small retry helper used by the manual retry example."""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import TypeVar

T = TypeVar("T")
logger = logging.getLogger(__name__)


async def retry_async(
    operation: Callable[[int], Awaitable[T]],
    *,
    max_attempts: int,
    retry_exceptions: tuple[type[Exception], ...],
    initial_delay_seconds: float = 0.1,
) -> tuple[T, int]:
    """Run an async operation until it succeeds or retry attempts are exhausted."""
    last_error: Exception | None = None

    for attempt in range(1, max_attempts + 1):
        try:
            return await operation(attempt), attempt
        except retry_exceptions as exc:
            last_error = exc
            logger.info("[manual_retry] attempt %s failed: %s", attempt, exc)
            if attempt == max_attempts:
                break
            await asyncio.sleep(initial_delay_seconds * attempt)

    if last_error is None:
        raise RuntimeError("retry_async exhausted without capturing an exception")
    raise last_error
