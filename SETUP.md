# Настройка портфель-анализатора

## Описание
Модернизированная система анализа инвестиционного портфеля с модульной архитектурой, расширенной обработкой ошибок и комплексным тестированием.

## Архитектура
```
portfolio_analyzer/
├── config.py              # Конфигурация через Pydantic
├── main.py                 # Главный модуль
├── models/                 # Модели данных
│   ├── __init__.py
│   └── state.py           # Portfolio, AnalysisResult
├── services/              # Сервисный слой
│   ├── __init__.py
│   ├── ai_service.py      # DeepSeek API
│   ├── news_service.py    # Новости (Lenta.ru, Tinkoff Pulse)
│   ├── moex_service.py    # Данные MOEX
│   └── ifrs_service.py    # IFRS отчетность
├── analyzers/             # Анализаторы
│   ├── __init__.py
│   ├── portfolio_analyzer.py    # Основной анализ
│   └── rebalancing_analyzer.py  # Ребалансировка
├── utils/                 # Утилиты
│   ├── __init__.py
│   ├── helpers.py         # Retry логика, обработка ошибок
│   └── monitoring.py      # Мониторинг производительности
└── tests/                 # Тесты
    ├── __init__.py
    ├── test_ai_service.py
    ├── test_models.py
    └── test_helpers.py
```

## Установка и настройка

### 1. Создание виртуального окружения
```bash
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate     # Windows
```

### 2. Установка зависимостей
```bash
pip install -r req.txt
```

### 3. Настройка переменных окружения
Скопируйте файл `.env.example` в `.env` и заполните необходимые значения:

```bash
cp .env.example .env
```

Отредактируйте `.env`:
```env
# DeepSeek API Configuration
DEEPSEEK_API_KEY=your_actual_api_key_here
DEEPSEEK_MODEL=deepseek-chat
DEEPSEEK_BASE_URL=https://api.deepseek.com

# Analysis Parameters
NEWS_DAYS_LOOKBACK=1
MOEX_DAYS_LOOKBACK=180
MAX_NEWS_ITEMS=3
MAX_IFRS_CONTENT_LENGTH=1500

# API Limits
API_TIMEOUT=30
MAX_RETRIES=3

# Optional: Logging Level
LOG_LEVEL=INFO
```

## Использование

### Основной анализ портфеля
```python
from main import analyze_portfolio_improved

# Определяем портфель
portfolio = {
    'SBER': 100,
    'GAZP': 50,
    'MGNT': 25
}

# Выполняем анализ
results = analyze_portfolio_improved(portfolio)
print_analysis_results(results)
```

### Использование отдельных компонентов
```python
from models import Portfolio
from analyzers import PortfolioAnalyzer
from services import NewsService, MOEXService

# Создание портфеля с валидацией
portfolio = Portfolio.from_dict({'SBER': 100})

# Работа с отдельными сервисами
news_service = NewsService()
market_news = news_service.get_market_news()
```

## Тестирование

### Запуск всех тестов
```bash
pytest
```

### Запуск тестов с покрытием
```bash
pytest --cov=. --cov-report=html
```

### Запуск конкретных тестов
```bash
# Только тесты моделей
pytest tests/test_models.py

# Только тесты AI сервиса
pytest tests/test_ai_service.py -v
```

## Мониторинг производительности

Система включает встроенный мониторинг производительности:

```python
from utils import get_performance_report, log_performance_summary

# Получить отчет о производительности
report = get_performance_report()
print(report)

# Логировать сводку производительности
log_performance_summary()
```

## Обработка ошибок

Система использует кастомные исключения и retry логику:

```python
from utils import APIError, DataProcessingError, retry_on_failure

@retry_on_failure(max_retries=3, delay=1.0)
def api_call():
    # Ваш API вызов
    pass
```

## Конфигурация

Все настройки управляются через `config.py` с использованием Pydantic:

```python
from config import settings

print(f"API Key: {settings.deepseek_api_key}")
print(f"Max retries: {settings.max_retries}")
```

## Валидация данных

Модели используют Pydantic для валидации:

```python
from models import PortfolioPosition

# Автоматическая валидация
position = PortfolioPosition(ticker="sber", quantity=100)
print(position.ticker)  # "SBER" (автоматически переведено в верхний регистр)

# Ошибка валидации
try:
    invalid_position = PortfolioPosition(ticker="AB", quantity=-10)
except ValidationError as e:
    print(e)
```

## Логирование

Настройка логирования в `main.py`:

```python
import logging

# Настройка уровня логирования из переменных окружения
logging.basicConfig(
    level=getattr(logging, settings.log_level, logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

## Расширение функциональности

### Добавление нового сервиса
1. Создайте новый файл в `services/`
2. Наследуйтесь от базового класса или следуйте существующему паттерну
3. Добавьте декоратор `@monitor_performance` для мониторинга
4. Обновите `services/__init__.py`

### Добавление новых тестов
1. Создайте тестовый файл в `tests/`
2. Используйте pytest фикстуры и мокирование
3. Запустите тесты для проверки

## Известные ограничения

1. **API лимиты**: DeepSeek API имеет ограничения на количество запросов
2. **Зависимость от внешних сервисов**: Требует доступа к MOEX, Lenta.ru, Tinkoff Pulse
3. **Время выполнения**: Анализ большого портфеля может занять несколько минут

## Поддержка

При возникновении проблем:
1. Проверьте логи в консоли
2. Убедитесь, что все переменные окружения настроены
3. Запустите тесты для проверки корректности установки
4. Проверьте отчет о производительности для выявления узких мест