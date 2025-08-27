import pytest
from unittest.mock import Mock, patch

from config import settings
from services.ai_service import AIService
from utils.helpers import APIError


class TestAIService:
    """Тесты для сервиса работы с LLM"""

    @pytest.fixture
    def deepseek_service(self, monkeypatch):
        monkeypatch.setenv('DEEPSEEK_API_KEY', 'test_key')
        monkeypatch.setattr(settings, 'llm_provider', 'deepseek')
        return AIService()

    @pytest.fixture
    def ollama_service(self, monkeypatch):
        monkeypatch.delenv('DEEPSEEK_API_KEY', raising=False)
        monkeypatch.setattr(settings, 'llm_provider', 'ollama')
        return AIService()

    @pytest.fixture
    def openai_service(self, monkeypatch):
        monkeypatch.delenv('DEEPSEEK_API_KEY', raising=False)
        monkeypatch.setenv('OPENAI_API_KEY', 'test_key')
        monkeypatch.setattr(settings, 'llm_provider', 'openai')
        return AIService()

    @patch('services.ai_service.OpenAI')
    def test_call_model_deepseek_success(self, mock_openai, deepseek_service):
        """Тест успешного вызова DeepSeek API"""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Test response"
        mock_openai.return_value.chat.completions.create.return_value = mock_response

        result = deepseek_service.call_model("system", "user")
        assert result == "Test response"

        mock_openai.return_value.chat.completions.create.assert_called_once()
        call_args = mock_openai.return_value.chat.completions.create.call_args
        assert call_args[1]['model'] == 'deepseek-chat'
        assert len(call_args[1]['messages']) == 2

    @patch('services.ai_service.OpenAI')
    def test_call_model_deepseek_api_error(self, mock_openai, deepseek_service):
        """Тест обработки ошибок API"""
        mock_openai.return_value.chat.completions.create.side_effect = Exception("API Error")

        with patch('time.sleep'):
            with pytest.raises(APIError):
                deepseek_service.call_model("system", "user")
        assert (
            mock_openai.return_value.chat.completions.create.call_count
            == settings.max_retries
        )

    @patch('services.ai_service.OpenAI')
    def test_call_model_deepseek_empty_response(self, mock_openai, deepseek_service):
        """Тест обработки пустого ответа"""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = ""
        mock_openai.return_value.chat.completions.create.return_value = mock_response

        result = deepseek_service.call_model("system", "user")
        assert result == ""

    def test_init_without_api_key(self, monkeypatch):
        """Тест инициализации без API ключа"""
        monkeypatch.delenv('DEEPSEEK_API_KEY', raising=False)
        monkeypatch.setattr(settings, 'llm_provider', 'deepseek')
        with pytest.raises(ValueError, match="DEEPSEEK_API_KEY must be set"):
            AIService()

    @patch('services.ai_service.OpenAI')
    def test_call_model_deepseek_with_retry(self, mock_openai, deepseek_service):
        """Тест повторных попыток при ошибке"""
        mock_openai.return_value.chat.completions.create.side_effect = [
            Exception("Temporary error"),
            Mock(choices=[Mock(message=Mock(content="Success after retry"))])
        ]
        with patch('time.sleep'):
            result = deepseek_service.call_model("system", "user")
        assert result == "Success after retry"
        assert mock_openai.return_value.chat.completions.create.call_count == 2

    @patch('services.ai_service.wrap_openai')
    @patch('services.ai_service.OpenAI')
    def test_wrap_openai_called_when_langsmith_enabled(self, mock_openai, mock_wrap):
        """Проверяем, что wrap_openai вызывается при активном LangSmith"""
        mock_openai.return_value.chat.completions.create.return_value = Mock(choices=[Mock(message=Mock(content="resp"))])
        with patch.dict('os.environ', {'DEEPSEEK_API_KEY': 'test_key', 'LANGCHAIN_API_KEY': 'ls_key'}):
            settings.llm_provider = 'deepseek'
            service = AIService()
            service.call_model("sys", "usr")
        mock_wrap.assert_called_once()

    @patch('ollama.Client')
    def test_call_model_ollama_success(self, mock_client, ollama_service):
        """Тест вызова локальной Ollama"""
        mock_client.return_value.chat.return_value = {'message': {'content': 'Hi'}}
        result = ollama_service.call_model("system", "user")
        assert result == 'Hi'
        mock_client.return_value.chat.assert_called_once()

    @patch('services.ai_service.OpenAI')
    def test_call_model_openai_success(self, mock_openai, openai_service):
        """Тест успешного вызова OpenAI API"""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "OpenAI response"
        mock_openai.return_value.chat.completions.create.return_value = mock_response

        result = openai_service.call_model("system", "user")
        assert result == "OpenAI response"

        mock_openai.return_value.chat.completions.create.assert_called_once()
        call_args = mock_openai.return_value.chat.completions.create.call_args
        assert call_args[1]['model'] == 'gpt-4o-mini'

    @patch('services.ai_service.OpenAI')
    def test_call_model_openai_api_error(self, mock_openai, openai_service):
        """Тест обработки ошибок OpenAI API"""
        mock_openai.return_value.chat.completions.create.side_effect = Exception("API Error")

        with patch('time.sleep'):
            with pytest.raises(APIError):
                openai_service.call_model("system", "user")
        assert (
            mock_openai.return_value.chat.completions.create.call_count
            == settings.max_retries
        )

    def test_openai_init_without_api_key(self, monkeypatch):
        monkeypatch.delenv('OPENAI_API_KEY', raising=False)
        monkeypatch.setattr(settings, 'llm_provider', 'openai')
        with pytest.raises(ValueError, match="OPENAI_API_KEY must be set"):
            AIService()
