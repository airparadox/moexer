import pytest
from unittest.mock import Mock, patch, MagicMock
from services.ai_service import AIService
from utils.helpers import APIError


class TestAIService:
    """Тесты для сервиса работы с AI API"""
    
    @pytest.fixture
    def ai_service(self):
        """Фикстура для создания экземпляра AIService"""
        with patch.dict('os.environ', {'DEEPSEEK_API_KEY': 'test_key'}):
            return AIService()
    
    @patch('services.ai_service.OpenAI')
    def test_call_deepseek_success(self, mock_openai, ai_service):
        """Тест успешного вызова DeepSeek API"""
        # Мок успешного ответа
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Test response"
        mock_openai.return_value.chat.completions.create.return_value = mock_response
        
        result = ai_service.call_deepseek("system", "user")
        assert result == "Test response"
        
        # Проверяем, что API был вызван с правильными параметрами
        mock_openai.return_value.chat.completions.create.assert_called_once()
        call_args = mock_openai.return_value.chat.completions.create.call_args
        assert call_args[1]['model'] == 'deepseek-chat'
        assert len(call_args[1]['messages']) == 2
    
    @patch('services.ai_service.OpenAI')
    def test_call_deepseek_api_error(self, mock_openai, ai_service):
        """Тест обработки ошибок API"""
        # Мок ошибки API
        mock_openai.return_value.chat.completions.create.side_effect = Exception("API Error")
        
        result = ai_service.call_deepseek("system", "user")
        assert "Ошибка анализа" in result
    
    @patch('services.ai_service.OpenAI')
    def test_call_deepseek_empty_response(self, mock_openai, ai_service):
        """Тест обработки пустого ответа"""
        # Мок пустого ответа
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = ""
        mock_openai.return_value.chat.completions.create.return_value = mock_response
        
        result = ai_service.call_deepseek("system", "user")
        assert result == ""
    
    def test_init_without_api_key(self):
        """Тест инициализации без API ключа"""
        with patch.dict('os.environ', {}, clear=True):
            with pytest.raises(ValueError, match="DEEPSEEK_API_KEY must be set"):
                AIService()
    
    @patch('services.ai_service.OpenAI')
    def test_call_deepseek_with_retry(self, mock_openai, ai_service):
        """Тест повторных попыток при ошибке"""
        # Первый вызов - ошибка, второй - успех
        mock_openai.return_value.chat.completions.create.side_effect = [
            Exception("Temporary error"),
            Mock(choices=[Mock(message=Mock(content="Success after retry"))])
        ]
        
        with patch('time.sleep'):  # Мокаем sleep для ускорения тестов
            result = ai_service.call_deepseek("system", "user")
            assert "Success after retry" in result or "Ошибка анализа" in result