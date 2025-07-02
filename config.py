from pydantic_settings import BaseSettings
from pydantic import validator


class Settings(BaseSettings):
    log_level: str = "INFO"  # Default value
    deepseek_api_key: str
    deepseek_model: str = "deepseek-chat"
    deepseek_base_url: str = "https://api.deepseek.com"
    
    # Параметры анализа
    news_days_lookback: int = 1
    moex_days_lookback: int = 180
    max_news_items: int = 3
    max_ifrs_content_length: int = 1500
    
    # Лимиты API
    api_timeout: int = 30
    max_retries: int = 3
    
    class Config:
        env_file = ".env"
        
    @validator('deepseek_api_key')
    def validate_api_key(cls, v):
        if not v:
            raise ValueError('DEEPSEEK_API_KEY must be set')
        return v

settings = Settings()
