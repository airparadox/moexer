import logging
import time
import requests
from functools import wraps
from typing import Callable, Any
from models.state import Portfolio
import re

logger = logging.getLogger(__name__)

class APIError(Exception):
    """Кастомное исключение для API ошибок"""
    pass

class DataProcessingError(Exception):
    """Кастомное исключение для ошибок обработки данных"""
    pass

def retry_on_failure(max_retries: int = 3, delay: float = 1.0):
    """Декоратор для повторных попыток при ошибках API"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except (requests.RequestException, ConnectionError) as e:
                    if attempt == max_retries - 1:
                        logger.error(f"Failed after {max_retries} attempts: {e}")
                        raise APIError(f"API call failed after {max_retries} attempts: {e}")
                    logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay}s...")
                    time.sleep(delay)
                except Exception as e:
                    logger.error(f"Unexpected error in {func.__name__}: {e}")
                    raise
        return wrapper
    return decorator

def has_only_ticker(text: str, ticker: str) -> bool:
    """Проверяет, содержит ли текст только указанный тикер"""
    tickers = re.findall(r'\b[A-Z]{3,4}\b', text)
    return bool(tickers) and all(t == ticker for t in tickers)

def truncate_text(text: str, max_length: int) -> str:
    """Обрезает текст до указанной длины"""
    if len(text) <= max_length:
        return text
    return text[:max_length] + "..."

def calculate_portfolio_value(portfolio: 'Portfolio', price_getter: Callable[[str], float]) -> float:
    """Возвращает стоимость портфеля, используя функцию получения цены."""
    total = 0.0
    for position in portfolio.positions:
        try:
            price = price_getter(position.ticker)
            total += price * position.quantity
        except Exception as e:
            logger.error(f"Price for {position.ticker} unavailable: {e}")
    return total
