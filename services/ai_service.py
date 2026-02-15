import logging
import os
import json
from typing import Optional, Any, List, Dict, Callable

# ❗ Жёстко указываем OTEL endpoint на локальный Langfuse
os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = "http://localhost:3000/api/public/otel"
os.environ["OTEL_EXPORTER_OTLP_PROTOCOL"] = "http/protobuf"

# Можно дополнительно отключить retries
os.environ["OTEL_EXPORTER_OTLP_TRACES_ENDPOINT"] = "http://localhost:3000/api/public/otel/v1/traces"

# (по желанию) чтобы точно не было cloud fallback
os.environ["LANGFUSE_HOST"] = "http://localhost:3000"


from langfuse import Langfuse
from config import settings
from utils.helpers import retry_on_failure, APIError
from utils.monitoring import monitor_performance

logger = logging.getLogger(__name__)

# ✅ ЖЁСТКО указываем локальный Langfuse
langfuse = None
if os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY"):
    langfuse = Langfuse(
        host="http://localhost:3000",
        public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
        secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
    )


class AIService:
    """Сервис для работы с LLM провайдерами (DeepSeek, OpenAI или локальная Ollama)"""

    def __init__(self, api_key: Optional[str] = None):
        self.provider = settings.llm_provider.lower()

        if self.provider != "ollama":
            raise ValueError("Этот сервис сейчас настроен только для ollama")

        self.client: Optional[Any] = None

    def _ensure_client(self):
        if self.client is None:
            from ollama import Client as OllamaClient
            self.client = OllamaClient(host=settings.ollama_base_url)

    @monitor_performance("ai_service")
    @retry_on_failure(max_retries=settings.max_retries)
    def call_model(self, system_prompt: str, user_prompt: str) -> str:
        """Вызов Ollama с отправкой трейса в локальный Langfuse"""
        self._ensure_client()

        try:
            trace = None
            generation = None

            # ✅ Создаём trace если Langfuse включён
            if langfuse:
                trace = langfuse.trace(
                    name="ollama-call",
                    input={
                        "system_prompt": system_prompt,
                        "user_prompt": user_prompt,
                    },
                )

                generation = trace.generation(
                    name=settings.ollama_model,
                    model=settings.ollama_model,
                    input=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                )

            # 🔹 Вызов Ollama
            response = self.client.chat(
                model=settings.ollama_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )

            output_text = response["message"]["content"]

            # ✅ Завершаем generation
            if generation:
                generation.end(
                    output=output_text,
                )

            return output_text

        except Exception as e:
            logger.error(f"Ollama API error: {e}")

            if langfuse:
                langfuse.event(
                    name="ollama-error",
                    input={"error": str(e)},
                )

            raise APIError(f"Ollama API error: {e}") from e

    def call_with_tools(
        self,
        messages: List[Dict[str, str]],
        tools: List[Dict[str, Any]],
        tool_funcs: Dict[str, Callable],
    ) -> str:
        raise ValueError("Tool calling не реализован для Ollama")
