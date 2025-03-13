import asyncio
import functools
import logging
import random
from typing import TypeVar, Callable, Any, Optional, Type, Union, Tuple

T = TypeVar("T")

logger = logging.getLogger(__name__)

def retry(
    max_attempts: int = 3,
    backoff_factor: float = 1.5,
    jitter: float = 0.1,
    exceptions: Union[Type[Exception], Tuple[Type[Exception], ...]] = Exception,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    A decorator that retries an async function on failure with exponential backoff.
    
    Args:
        max_attempts: Maximum number of retry attempts before giving up
        backoff_factor: Multiplicative factor for exponential backoff
        jitter: Random jitter factor to add to delay (0.0 to 1.0)
        exceptions: Exception or tuple of exceptions to catch and retry on
        
    Returns:
        Decorated function that implements retry logic
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception: Optional[Exception] = None
            
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt == max_attempts - 1:
                        logger.error(
                            f"Final retry attempt {attempt + 1}/{max_attempts} failed for {func.__name__}",
                            exc_info=True
                        )
                        raise
                    
                    # Calculate delay with exponential backoff and jitter
                    delay = backoff_factor ** attempt
                    jitter_amount = random.uniform(-jitter * delay, jitter * delay)
                    total_delay = delay + jitter_amount
                    
                    logger.warning(
                        f"Retry attempt {attempt + 1}/{max_attempts} for {func.__name__} "
                        f"failed. Retrying in {total_delay:.2f}s"
                    )
                    
                    await asyncio.sleep(total_delay)
            
            # This should never be reached due to the raise in the last iteration
            assert last_exception is not None
            raise last_exception
            
        return wrapper
    
    return decorator
