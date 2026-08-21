"""AUSHADHI — retry decorator with exponential backoff.

Targets the transient failures seen against Gemini / Firestore / Pub/Sub:
503 UNAVAILABLE (server overload), 429 RESOURCE_EXHAUSTED, 500, timeouts.
Mirrors the retry policy validated in scripts/test_gemini_outbreak.py.

Usage:
    @retry(max_attempts=4, initial_delay=8.0)
    def call_gemini(...): ...

    @retry()
    async def fetch_inventory(...): ...
"""

import asyncio
import functools
import random
import time
from typing import Callable, Iterable, Tuple, TypeVar

from utils.logger import get_logger

log = get_logger(__name__)

T = TypeVar("T")

RETRYABLE_MARKERS: Tuple[str, ...] = (
    "503",
    "UNAVAILABLE",
    "429",
    "RESOURCE_EXHAUSTED",
    "500",
    "INTERNAL",
    "DEADLINE_EXCEEDED",
    "deadline exceeded",
    "connection reset",
    "temporarily unavailable",
)


def is_retryable(exc: BaseException, markers: Iterable[str] = RETRYABLE_MARKERS) -> bool:
    """True when the exception looks like a transient server-side failure."""
    if isinstance(exc, (TimeoutError, ConnectionError, asyncio.TimeoutError)):
        return True
    text = f"{type(exc).__name__}: {exc}"
    lowered = text.lower()
    return any(marker.lower() in lowered for marker in markers)


def _next_delay(delay: float, backoff_factor: float, max_delay: float, jitter: bool) -> float:
    delay = min(delay * backoff_factor, max_delay)
    if jitter:
        delay = delay * random.uniform(0.8, 1.2)
    return delay


def retry(
    max_attempts: int = 4,
    initial_delay: float = 8.0,
    backoff_factor: float = 2.0,
    max_delay: float = 60.0,
    jitter: bool = True,
    retryable_markers: Iterable[str] = RETRYABLE_MARKERS,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Retry a sync or async callable with exponential backoff on transient errors.

    Non-retryable exceptions (bad request, auth, validation) are raised immediately.
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        if asyncio.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                delay = initial_delay
                for attempt in range(1, max_attempts + 1):
                    try:
                        return await func(*args, **kwargs)
                    except Exception as exc:
                        if attempt >= max_attempts or not is_retryable(exc, retryable_markers):
                            log.error(
                                "retry_exhausted",
                                function=func.__qualname__,
                                attempt=attempt,
                                max_attempts=max_attempts,
                                error_type=type(exc).__name__,
                                error=str(exc),
                            )
                            raise
                        log.warning(
                            "retry_attempt_failed",
                            function=func.__qualname__,
                            attempt=attempt,
                            max_attempts=max_attempts,
                            retry_in_seconds=round(delay, 1),
                            error_type=type(exc).__name__,
                            error=str(exc),
                        )
                        await asyncio.sleep(delay)
                        delay = _next_delay(delay, backoff_factor, max_delay, jitter)

            return async_wrapper

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            delay = initial_delay
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as exc:
                    if attempt >= max_attempts or not is_retryable(exc, retryable_markers):
                        log.error(
                            "retry_exhausted",
                            function=func.__qualname__,
                            attempt=attempt,
                            max_attempts=max_attempts,
                            error_type=type(exc).__name__,
                            error=str(exc),
                        )
                        raise
                    log.warning(
                        "retry_attempt_failed",
                        function=func.__qualname__,
                        attempt=attempt,
                        max_attempts=max_attempts,
                        retry_in_seconds=round(delay, 1),
                        error_type=type(exc).__name__,
                        error=str(exc),
                    )
                    time.sleep(delay)
                    delay = _next_delay(delay, backoff_factor, max_delay, jitter)

        return sync_wrapper

    return decorator
