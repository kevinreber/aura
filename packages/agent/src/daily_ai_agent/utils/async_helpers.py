"""Async utility functions for the Daily AI Agent."""

import asyncio
from typing import Any, Callable, TypeVar, Optional, List
from functools import wraps
from loguru import logger

T = TypeVar("T")


def run_async(func: Callable[..., T]) -> Callable[..., T]:
    """
    Decorator to run an async function synchronously.

    This is useful for wrapping async functions in sync contexts
    like LangChain tool _run methods.

    Args:
        func: The async function to wrap

    Returns:
        A sync wrapper that runs the async function
    """

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> T:
        return asyncio.run(func(*args, **kwargs))

    return wrapper


async def gather_with_timeout(
    *coros: Any,
    timeout: float = 30.0,
    return_exceptions: bool = True,
) -> List[Any]:
    """
    Run multiple coroutines concurrently with a timeout.

    Args:
        *coros: Coroutines to run
        timeout: Maximum time to wait in seconds
        return_exceptions: If True, exceptions are returned instead of raised

    Returns:
        List of results (or exceptions if return_exceptions=True)
    """
    try:
        return await asyncio.wait_for(
            asyncio.gather(*coros, return_exceptions=return_exceptions),
            timeout=timeout,
        )
    except asyncio.TimeoutError:
        logger.error(f"Async gather timed out after {timeout}s")
        raise


async def retry_async(
    func: Callable[..., T],
    *args: Any,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 16.0,
    exponential_base: float = 2.0,
    retryable_exceptions: tuple = (Exception,),
    **kwargs: Any,
) -> T:
    """
    Retry an async function with exponential backoff.

    Args:
        func: The async function to call
        *args: Positional arguments for the function
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
        exponential_base: Base for exponential backoff calculation
        retryable_exceptions: Tuple of exception types to retry on
        **kwargs: Keyword arguments for the function

    Returns:
        The function result

    Raises:
        The last exception if all retries fail
    """
    last_exception: Optional[Exception] = None
    delay = base_delay

    for attempt in range(max_retries + 1):
        try:
            if asyncio.iscoroutinefunction(func):
                return await func(*args, **kwargs)
            return func(*args, **kwargs)
        except retryable_exceptions as e:
            last_exception = e
            if attempt < max_retries:
                logger.warning(
                    f"Attempt {attempt + 1}/{max_retries + 1} failed: {e}. "
                    f"Retrying in {delay:.1f}s..."
                )
                await asyncio.sleep(delay)
                delay = min(delay * exponential_base, max_delay)
            else:
                logger.error(f"All {max_retries + 1} attempts failed: {e}")

    raise last_exception


class AsyncBatcher:
    """Batch multiple async operations for efficient execution."""

    def __init__(self, batch_size: int = 10, timeout: float = 30.0):
        """
        Initialize the async batcher.

        Args:
            batch_size: Maximum number of operations per batch
            timeout: Timeout for each batch in seconds
        """
        self.batch_size = batch_size
        self.timeout = timeout
        self._pending: List[Any] = []

    async def add(self, coro: Any) -> None:
        """Add a coroutine to the batch."""
        self._pending.append(coro)

    async def execute(self) -> List[Any]:
        """Execute all pending coroutines in batches."""
        results = []
        for i in range(0, len(self._pending), self.batch_size):
            batch = self._pending[i : i + self.batch_size]
            batch_results = await gather_with_timeout(
                *batch, timeout=self.timeout, return_exceptions=True
            )
            results.extend(batch_results)
        self._pending = []
        return results
