import os
import csv
from functools import lru_cache
from typing import Dict

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    log_level: str = "INFO"  # Default value

    # LLM provider configuration
    llm_provider: str = os.getenv("LLM_PROVIDER", "deepseek")
    deepseek_api_key: str | None = os.getenv("DEEPSEEK_API_KEY")
    deepseek_model: str = "deepseek-chat"
    deepseek_base_url: str = "https://api.deepseek.com"
    openai_api_key: str | None = os.getenv("OPENAI_API_KEY")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    openai_base_url: str | None = os.getenv("OPENAI_BASE_URL")
    openrouter_api_key: str | None = os.getenv("OPENROUTER_API_KEY")
    openrouter_model: str = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    ollama_model: str = os.getenv("OLLAMA_MODEL", "llama3:8b")
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

    # Langfuse configuration
    langfuse_host: str = os.getenv("LANGFUSE_HOST", "http://localhost:3000")
    
    # Параметры анализа
    news_days_lookback: int = 1
    moex_days_lookback: int = 180
    max_news_items: int = 100
    max_ifrs_content_length: int = 15000

    # Лимиты API
    api_timeout: int = 30
    max_retries: int = 3
    max_concurrent_tasks: int = 20

    # Конфигурация модулей анализа
    module_config_file: str = os.getenv("MODULE_CONFIG_FILE", "modules.csv")
    

settings = Settings()


def load_module_config(path: str) -> Dict[str, Dict[str, float | bool]]:
    """Load module configuration from CSV file."""
    modules: Dict[str, Dict[str, float | bool]] = {}
    try:
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            for row in reader:
                if not row or row[0].startswith("#"):
                    continue
                name, enabled, weight = row[0].strip(), row[1].strip(), row[2].strip()
                modules[name] = {"enabled": enabled == "1", "weight": float(weight)}
    except FileNotFoundError:
        modules = {
            "ifrs": {"enabled": True, "weight": 0.55},
            "market_news": {"enabled": True, "weight": 0.20},
            "moex": {"enabled": True, "weight": 0.15},
            "social": {"enabled": True, "weight": 0.10},
        }
    return modules


@lru_cache(maxsize=1)
def get_modules_config() -> Dict[str, Dict[str, float | bool]]:
    """Cached accessor for module configuration."""
    return load_module_config(settings.module_config_file)
