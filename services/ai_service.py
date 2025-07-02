import logging
from openai import OpenAI
from typing import Optional
import os
from config import settings
from utils.helpers import retry_on_failure, APIError
from utils.monitoring import monitor_performance

logger = logging.getLogger(__name__)

class AIService:
    """Сервис для работы с DeepSeek API"""
    
    def __init__(self, api_key: Optional[str] = None):
        env_key = os.getenv("DEEPSEEK_API_KEY")
        self.api_key = api_key or env_key
        if not self.api_key:
            raise ValueError("DEEPSEEK_API_KEY must be set")
        self.client: Optional[OpenAI] = None

    def _ensure_client(self):
        if self.client is None:
            self.client = OpenAI(
                api_key=self.api_key,
                base_url=settings.deepseek_base_url,
            )
    
    @monitor_performance("ai_service")
    @retry_on_failure(max_retries=settings.max_retries)
    def call_deepseek(self, system_prompt: str, user_prompt: str) -> str:
        """
        Унифицированный вызов DeepSeek API с поддержкой Context Caching
        
        Args:
            system_prompt: Системное сообщение
            user_prompt: Пользовательское сообщение
            
        Returns:
            Ответ от API
            
        Raises:
            APIError: При ошибках API
        """
        try:
            self._ensure_client()
            response = self.client.chat.completions.create(
                model=settings.deepseek_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=1,
                stream=False
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"DeepSeek API error: {e}")
            return "Ошибка анализа"
