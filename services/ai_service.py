import logging
import os
from typing import Optional, Any, List, Dict, Callable

from openai import OpenAI

from config import settings
from utils.helpers import retry_on_failure, APIError
from utils.monitoring import monitor_performance

try:
    from langfuse import openai as langfuse_openai
except Exception:  # pragma: no cover - fallback for environments without langfuse
    class _LangfuseOpenAIStub:
        @staticmethod
        def register_tracing(*args, **kwargs):
            return None

    langfuse_openai = _LangfuseOpenAIStub()

logger = logging.getLogger(__name__)


class AIService:
    """Сервис для работы с LLM провайдерами (DeepSeek, OpenAI, OpenRouter или локальная Ollama)."""

    def __init__(self, api_key: Optional[str] = None):
        self.provider = settings.llm_provider.lower()
        self.client: Optional[Any] = None
        self.api_key = api_key

        if self.provider == "deepseek":
            self.api_key = api_key or settings.deepseek_api_key or os.getenv("DEEPSEEK_API_KEY")
            if not self.api_key:
                raise ValueError("DEEPSEEK_API_KEY must be set")
        elif self.provider == "openai":
            self.api_key = api_key or settings.openai_api_key or os.getenv("OPENAI_API_KEY")
            if not self.api_key:
                raise ValueError("OPENAI_API_KEY must be set")
        elif self.provider == "openrouter":
            self.api_key = api_key or settings.openrouter_api_key or os.getenv("OPENROUTER_API_KEY")
            if not self.api_key:
                raise ValueError("OPENROUTER_API_KEY must be set")
        elif self.provider == "ollama":
            self.api_key = None
        else:
            raise ValueError(f"Unsupported LLM provider: {self.provider}")

    def _ensure_client(self):
        if self.client is not None:
            return

        if self.provider == "ollama":
            from ollama import Client as OllamaClient

            self.client = OllamaClient(host=settings.ollama_base_url)
            return

        if self.provider == "deepseek":
            base_url = settings.deepseek_base_url
        elif self.provider == "openai":
            base_url = settings.openai_base_url
        elif self.provider == "openrouter":
            base_url = settings.openrouter_base_url
        else:
            base_url = None
            
        if base_url and not base_url.rstrip("/").endswith("/v1"):
            base_url = f"{base_url.rstrip('/')}/v1"

        self.client = OpenAI(api_key=self.api_key, base_url=base_url)

        if os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY"):
            os.environ.setdefault("LANGFUSE_HOST", settings.langfuse_host)
            langfuse_openai.register_tracing()

    @monitor_performance("ai_service")
    @retry_on_failure(max_retries=settings.max_retries)
    def call_model(self, system_prompt: str, user_prompt: str) -> str:
        self._ensure_client()

        try:
            if self.provider == "ollama":
                response = self.client.chat(
                    model=settings.ollama_model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                )
                return response["message"]["content"]

            if self.provider == "deepseek":
                model = settings.deepseek_model
            elif self.provider == "openai":
                model = settings.openai_model
            elif self.provider == "openrouter":
                model = settings.openrouter_model
            else:
                raise ValueError(f"Unsupported LLM provider: {self.provider}")
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            return response.choices[0].message.content or ""

        except Exception as e:
            logger.error("%s API error: %s", self.provider, e)
            raise APIError(f"{self.provider} API error: {e}") from e

    def call_with_tools(
        self,
        messages: List[Dict[str, str]],
        tools: List[Dict[str, Any]],
        tool_funcs: Dict[str, Callable],
    ) -> str:
        raise ValueError("Tool calling не реализован")
