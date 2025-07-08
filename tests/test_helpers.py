import pytest
from unittest.mock import patch, Mock
import requests
from utils.helpers import (
    retry_on_failure,
    has_only_ticker,
    truncate_text,
    extract_recommendation,
    APIError,
    DataProcessingError,
)


class TestRetryDecorator:
    """Тесты для декоратора retry_on_failure"""
    
    def test_success_on_first_try(self):
        """Тест успешного выполнения с первой попытки"""
        @retry_on_failure(max_retries=3, delay=0.1)
        def successful_function():
            return "success"
        
        result = successful_function()
        assert result == "success"
    
    def test_success_after_retries(self):
        """Тест успешного выполнения после нескольких попыток"""
        call_count = 0
        
        @retry_on_failure(max_retries=3, delay=0.1)
        def function_with_retries():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise requests.RequestException("Temporary error")
            return "success after retries"
        
        with patch('time.sleep'):  # Мокаем sleep для ускорения тестов
            result = function_with_retries()
            assert result == "success after retries"
            assert call_count == 3
    
    def test_max_retries_exceeded(self):
        """Тест превышения максимального количества попыток"""
        @retry_on_failure(max_retries=2, delay=0.1)
        def always_failing_function():
            raise requests.RequestException("Persistent error")
        
        with patch('time.sleep'):
            with pytest.raises(APIError) as exc_info:
                always_failing_function()
            assert "API call failed after 2 attempts" in str(exc_info.value)
    
    def test_unexpected_error(self):
        """Тест обработки неожиданных ошибок"""
        @retry_on_failure(max_retries=3, delay=0.1)
        def function_with_unexpected_error():
            raise ValueError("Unexpected error")
        
        with pytest.raises(ValueError, match="Unexpected error"):
            function_with_unexpected_error()
    
    def test_connection_error_retry(self):
        """Тест повторных попыток при ошибке соединения"""
        call_count = 0
        
        @retry_on_failure(max_retries=2, delay=0.1)
        def function_with_connection_error():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ConnectionError("Connection failed")
            return "success"
        
        with patch('time.sleep'):
            result = function_with_connection_error()
            assert result == "success"
            assert call_count == 2


class TestTickerHelpers:
    """Тесты для вспомогательных функций работы с тикерами"""
    
    def test_has_only_ticker_single_match(self):
        """Тест функции has_only_ticker с одним совпадением"""
        text = "Акции SBER показали рост"
        assert has_only_ticker(text, "SBER") is True
    
    def test_has_only_ticker_multiple_same(self):
        """Тест функции has_only_ticker с несколькими одинаковыми тикерами"""
        text = "SBER и снова SBER демонстрируют стабильность"
        assert has_only_ticker(text, "SBER") is True
    
    def test_has_only_ticker_different_tickers(self):
        """Тест функции has_only_ticker с разными тикерами"""
        text = "SBER и GAZP показали разные результаты"
        assert has_only_ticker(text, "SBER") is False
    
    def test_has_only_ticker_no_tickers(self):
        """Тест функции has_only_ticker без тикеров"""
        text = "Общие новости рынка без конкретных тикеров"
        assert has_only_ticker(text, "SBER") is False
    
    def test_has_only_ticker_wrong_ticker(self):
        """Тест функции has_only_ticker с неправильным тикером"""
        text = "Акции GAZP выросли"
        assert has_only_ticker(text, "SBER") is False
    
    def test_has_only_ticker_case_sensitivity(self):
        """Тест функции has_only_ticker на чувствительность к регистру"""
        text = "Акции sber показали рост"  # Нижний регистр
        assert has_only_ticker(text, "SBER") is False  # Функция ищет только заглавные
    
    def test_has_only_ticker_short_ticker(self):
        """Тест функции has_only_ticker с коротким тикером"""
        text = "RU показал рост"  # Короткий тикер не должен захватываться
        assert has_only_ticker(text, "RU") is False


class TestTextHelpers:
    """Тесты для вспомогательных функций работы с текстом"""
    
    def test_truncate_text_short(self):
        """Тест обрезания короткого текста"""
        text = "Короткий текст"
        result = truncate_text(text, 100)
        assert result == text
    
    def test_truncate_text_exact_length(self):
        """Тест обрезания текста точной длины"""
        text = "Текст длиной 20 сим"  # Ровно 20 символов
        result = truncate_text(text, 20)
        assert result == text
    
    def test_truncate_text_long(self):
        """Тест обрезания длинного текста"""
        text = "Очень длинный текст, который нужно обрезать"
        result = truncate_text(text, 20)
        assert result == "Очень длинный текст,..."
        assert len(result) == 23  # 20 символов + "..."
    
    def test_truncate_text_empty(self):
        """Тест обрезания пустого текста"""
        text = ""
        result = truncate_text(text, 10)
        assert result == ""
    
    def test_truncate_text_zero_length(self):
        """Тест обрезания с нулевой длиной"""
        text = "Любой текст"
        result = truncate_text(text, 0)
        assert result == "..."

    def test_extract_recommendation_explicit(self):
        """Извлекается явная рекомендация"""
        text = "Решение: \nРекомендация: **ПРОДАВАТЬ**. Стоит избегать."
        assert extract_recommendation(text) == "ПРОДАВАТЬ"

    def test_extract_recommendation_fallback(self):
        """Фолбек работает при отсутствии ключевой строки"""
        text = "Компания хороша, можно КУПИТЬ при снижении."
        assert extract_recommendation(text) == "КУПИТЬ"


class TestCustomExceptions:
    """Тесты для кастомных исключений"""
    
    def test_api_error(self):
        """Тест исключения APIError"""
        with pytest.raises(APIError) as exc_info:
            raise APIError("Test API error")
        assert str(exc_info.value) == "Test API error"
    
    def test_data_processing_error(self):
        """Тест исключения DataProcessingError"""
        with pytest.raises(DataProcessingError) as exc_info:
            raise DataProcessingError("Test data processing error")
        assert str(exc_info.value) == "Test data processing error"
    
    def test_exceptions_inheritance(self):
        """Тест наследования исключений"""
        assert issubclass(APIError, Exception)
        assert issubclass(DataProcessingError, Exception)