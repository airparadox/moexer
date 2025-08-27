import os
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
    ollama_model: str = os.getenv("OLLAMA_MODEL", "llama3:8b")
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    
    # Параметры анализа
    news_days_lookback: int = 1
    moex_days_lookback: int = 180
    max_news_items: int = 3
    max_ifrs_content_length: int = 1500

    # Лимиты API
    api_timeout: int = 30
    max_retries: int = 3
    max_concurrent_tasks: int = 20
    

settings = Settings()
