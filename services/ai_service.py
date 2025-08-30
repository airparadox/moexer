import logging
import os
from typing import Optional, Any

from openai import OpenAI
import langfuse.openai as langfuse_openai

from config import settings
from utils.helpers import retry_on_failure, APIError
from utils.monitoring import monitor_performance

logger = logging.getLogger(__name__)

class AIService:
    """Сервис для работы с LLM провайдерами (DeepSeek, OpenAI или локальная Ollama)"""

    def __init__(self, api_key: Optional[str] = None):
        self.provider = settings.llm_provider.lower()
        if self.provider == "chatgpt":
            self.provider = "openai"

        if self.provider == "deepseek":
            env_key = os.getenv("DEEPSEEK_API_KEY")
            self.api_key = api_key or env_key
            if not self.api_key:
                raise ValueError("DEEPSEEK_API_KEY must be set")
        elif self.provider == "openai":
            env_key = os.getenv("OPENAI_API_KEY")
            self.api_key = api_key or env_key
            if not self.api_key:
                raise ValueError("OPENAI_API_KEY must be set")
        else:
            self.api_key = None
        self.client: Optional[Any] = None

    def _ensure_client(self):
        if self.client is None:
            if self.provider in {"deepseek", "openai"}:
                if os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY"):
                    langfuse_openai.register_tracing()
            if self.provider == "deepseek":
                client = OpenAI(
                    api_key=self.api_key,
                    base_url=settings.deepseek_base_url,
                )
                self.client = client
            elif self.provider == "openai":
                kwargs = {"api_key": self.api_key}
                if settings.openai_base_url:
                    kwargs["base_url"] = settings.openai_base_url
                client = OpenAI(**kwargs)
                self.client = client
            elif self.provider == "ollama":
                from ollama import Client as OllamaClient

                self.client = OllamaClient(host=settings.ollama_base_url)
    
    @monitor_performance("ai_service")
    @retry_on_failure(max_retries=settings.max_retries)
    def call_model(self, system_prompt: str, user_prompt: str) -> str:
        """Унифицированный вызов LLM"""
        self._ensure_client()
        try:
            if self.provider == "deepseek":
                response = self.client.chat.completions.create(
                    model=settings.deepseek_model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=1,
                    stream=False,
                )
                return response.choices[0].message.content
            elif self.provider == "openai":
                response = self.client.chat.completions.create(
                    model=settings.openai_model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=1,
                    stream=False,
                )
                return response.choices[0].message.content
            elif self.provider == "ollama":
                response = self.client.chat(
                    model=settings.ollama_model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                )
                return response["message"]["content"]
            else:
                raise ValueError(f"Unsupported provider: {self.provider}")
        except Exception as e:
            logger.error(f"{self.provider.capitalize()} API error: {e}")
            raise APIError(f"{self.provider.capitalize()} API error: {e}") from e
