# task_utils.py
import asyncio
import logging
from functools import wraps
from typing import Callable, Any

logger = logging.getLogger(__name__)


def retry_on_failure(max_retries: int = 2, delay: float = 1.0) -> Callable:
    """
    Асинхронный декоратор для повтора операций при ошибке.
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        logger.warning(f"Попытка {attempt + 1} неудачна ({func.__name__}): {e}. Повтор через {delay}s")
                        await asyncio.sleep(delay)
            # если все попытки не удались — пробрасываем последнюю ошибку
            raise last_exception
        return wrapper
    return decorator
