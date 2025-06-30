# Анализ кода и предложения по улучшению

## Обзор проекта
Проект представляет собой систему анализа портфеля акций, которая использует множество источников данных (Tinkoff Pulse, MOEX, новости, IFRS отчетность) и DeepSeek API для генерации инвестиционных рекомендаций.

## Основные проблемы и предложения по улучшению

### 1. Архитектура и структура кода

#### Проблемы:
- Весь код находится в одном файле `main.py` (266 строк)
- Отсутствие разделения на модули и классы
- Нарушение принципа единственной ответственности

#### Рекомендации:
```
portfolio_analyzer/
├── __init__.py
├── config.py           # Конфигурация и константы
├── models/
│   ├── __init__.py
│   └── state.py        # Модели данных
├── services/
│   ├── __init__.py
│   ├── news_service.py
│   ├── moex_service.py
│   ├── ifrs_service.py
│   └── ai_service.py
├── analyzers/
│   ├── __init__.py
│   ├── portfolio_analyzer.py
│   └── rebalancing_analyzer.py
└── utils/
    ├── __init__.py
    └── helpers.py
```

### 2. Обработка ошибок и логирование

#### Проблемы:
- Широкие `except Exception` блоки
- Недостаточно информативные сообщения об ошибках
- Отсутствие retry механизмов для API вызовов

#### Рекомендации:
```python
import logging
from functools import wraps
from typing import Optional
import time

def retry_on_failure(max_retries: int = 3, delay: float = 1.0):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except (requests.RequestException, ConnectionError) as e:
                    if attempt == max_retries - 1:
                        logger.error(f"Failed after {max_retries} attempts: {e}")
                        raise
                    logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay}s...")
                    time.sleep(delay)
        return wrapper
    return decorator

class APIError(Exception):
    """Кастомное исключение для API ошибок"""
    pass

class DataProcessingError(Exception):
    """Кастомное исключение для ошибок обработки данных"""
    pass
```

### 3. Конфигурация и переменные окружения

#### Проблемы:
- Хардкодированные значения
- Отсутствие валидации переменных окружения
- Нет настроек для различных окружений

#### Рекомендации:
```python
from pydantic import BaseSettings, validator
from typing import Optional

class Settings(BaseSettings):
    deepseek_api_key: str
    deepseek_model: str = "deepseek-chat"
    deepseek_base_url: str = "https://api.deepseek.com"
    
    # Параметры анализа
    news_days_lookback: int = 1
    moex_days_lookback: int = 180
    max_news_items: int = 3
    max_ifrs_content_length: int = 1500
    
    # Лимиты API
    api_timeout: int = 30
    max_retries: int = 3
    
    class Config:
        env_file = ".env"
        
    @validator('deepseek_api_key')
    def validate_api_key(cls, v):
        if not v:
            raise ValueError('DEEPSEEK_API_KEY must be set')
        return v

settings = Settings()
```

### 4. Работа с данными

#### Проблемы:
- Неэффективная обработка DataFrame
- Отсутствие кеширования данных
- Нет валидации входных данных

#### Рекомендации:
```python
from pydantic import BaseModel, validator
from typing import Dict, List, Optional
import pandas as pd
from functools import lru_cache

class PortfolioPosition(BaseModel):
    ticker: str
    quantity: int
    
    @validator('ticker')
    def validate_ticker(cls, v):
        if not v or len(v) < 3:
            raise ValueError('Ticker must be at least 3 characters')
        return v.upper()
    
    @validator('quantity')
    def validate_quantity(cls, v):
        if v <= 0:
            raise ValueError('Quantity must be positive')
        return v

class Portfolio(BaseModel):
    positions: List[PortfolioPosition]
    
    @classmethod
    def from_dict(cls, data: Dict[str, int]):
        positions = [PortfolioPosition(ticker=k, quantity=v) for k, v in data.items()]
        return cls(positions=positions)

@lru_cache(maxsize=128)
def get_moex_data_cached(ticker: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
    """Кешированное получение данных MOEX"""
    # Реализация получения данных
    pass
```

### 5. Безопасность и производительность

#### Проблемы:
- Отсутствие rate limiting для API
- Синхронная обработка портфеля
- Нет ограничений на размер данных

#### Рекомендации:
```python
import asyncio
import aiohttp
from asyncio import Semaphore

class AsyncPortfolioAnalyzer:
    def __init__(self, max_concurrent_requests: int = 5):
        self.semaphore = Semaphore(max_concurrent_requests)
    
    async def analyze_ticker(self, session: aiohttp.ClientSession, ticker: str) -> dict:
        async with self.semaphore:
            # Асинхронный анализ тикера
            pass
    
    async def analyze_portfolio(self, portfolio: Portfolio) -> dict:
        async with aiohttp.ClientSession() as session:
            tasks = [
                self.analyze_ticker(session, pos.ticker) 
                for pos in portfolio.positions
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            return self._process_results(results)
```

### 6. Тестирование

#### Проблемы:
- Отсутствие тестов
- Сложность тестирования из-за внешних зависимостей

#### Рекомендации:
```python
import pytest
from unittest.mock import Mock, patch
from portfolio_analyzer.services.ai_service import AIService

class TestAIService:
    @pytest.fixture
    def ai_service(self):
        return AIService(api_key="test_key")
    
    @patch('portfolio_analyzer.services.ai_service.OpenAI')
    def test_call_deepseek_success(self, mock_openai, ai_service):
        # Мок успешного ответа
        mock_response = Mock()
        mock_response.choices[0].message.content = "Test response"
        mock_openai.return_value.chat.completions.create.return_value = mock_response
        
        result = ai_service.call_deepseek("system", "user")
        assert result == "Test response"
    
    @patch('portfolio_analyzer.services.ai_service.OpenAI')
    def test_call_deepseek_api_error(self, mock_openai, ai_service):
        # Тест обработки ошибок API
        mock_openai.return_value.chat.completions.create.side_effect = Exception("API Error")
        
        result = ai_service.call_deepseek("system", "user")
        assert "Ошибка анализа" in result
```

### 7. Мониторинг и метрики

#### Рекомендации:
```python
import time
from functools import wraps
from prometheus_client import Counter, Histogram, start_http_server

# Метрики
API_CALLS = Counter('api_calls_total', 'Total API calls', ['service', 'status'])
PROCESSING_TIME = Histogram('processing_time_seconds', 'Time spent processing')

def monitor_performance(service_name: str):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                API_CALLS.labels(service=service_name, status='success').inc()
                return result
            except Exception as e:
                API_CALLS.labels(service=service_name, status='error').inc()
                raise
            finally:
                PROCESSING_TIME.observe(time.time() - start_time)
        return wrapper
    return decorator
```

### 8. Документация кода

#### Рекомендации:
```python
from typing import Dict, List, Optional
from dataclasses import dataclass

@dataclass
class AnalysisResult:
    """
    Результат анализа тикера.
    
    Attributes:
        ticker: Тикер инструмента
        recommendation: Рекомендация (КУПИТЬ/ДЕРЖАТЬ/ПРОДАВАТЬ)
        confidence: Уровень уверенности (0-1)
        analysis_data: Детальные данные анализа
    """
    ticker: str
    recommendation: str
    confidence: float
    analysis_data: Dict[str, str]

def analyze_portfolio(portfolio: Portfolio) -> Dict[str, AnalysisResult]:
    """
    Анализирует портфель и возвращает рекомендации по каждому тикеру.
    
    Args:
        portfolio: Портфель для анализа
        
    Returns:
        Словарь с результатами анализа для каждого тикера
        
    Raises:
        APIError: При ошибках обращения к внешним API
        DataProcessingError: При ошибках обработки данных
        
    Example:
        >>> portfolio = Portfolio.from_dict({'SBER': 100, 'GAZP': 50})
        >>> results = analyze_portfolio(portfolio)
        >>> print(results['SBER'].recommendation)
        'ДЕРЖАТЬ'
    """
    pass
```

## Итоговые рекомендации по приоритетам

1. **Высокий приоритет:**
   - Разделение кода на модули
   - Улучшение обработки ошибок
   - Добавление конфигурации через переменные окружения
   - Валидация входных данных

2. **Средний приоритет:**
   - Асинхронная обработка
   - Кеширование данных
   - Добавление метрик и мониторинга
   - Написание тестов

3. **Низкий приоритет:**
   - Оптимизация производительности
   - Расширенная документация
   - CI/CD pipeline
   - Веб-интерфейс

## Дополнительные улучшения

### Конфигурационный файл для стратегий анализа
```yaml
analysis_strategies:
  conservative:
    news_weight: 0.3
    technical_weight: 0.4
    financial_weight: 0.3
  aggressive:
    news_weight: 0.5
    technical_weight: 0.3
    financial_weight: 0.2
```

### Система уведомлений
```python
from enum import Enum
from abc import ABC, abstractmethod

class NotificationLevel(Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"

class NotificationService(ABC):
    @abstractmethod
    async def send(self, message: str, level: NotificationLevel):
        pass

class TelegramNotifier(NotificationService):
    async def send(self, message: str, level: NotificationLevel):
        # Отправка в Telegram
        pass
```

Эти улучшения сделают код более надежным, поддерживаемым и масштабируемым.