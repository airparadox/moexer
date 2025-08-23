from datetime import datetime
from pydantic import BaseModel, validator

class RecommendationRecord(BaseModel):
    """Модель записи рекомендации для хранения в БД."""
    ticker: str
    recommendation: str
    confidence: float
    price: float
    timestamp: datetime

    @validator("ticker")
    def validate_ticker(cls, v: str) -> str:
        if not v or len(v) < 2:
            raise ValueError("Ticker must be at least 2 characters")
        return v.upper()

    @validator("confidence")
    def validate_confidence(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError("Confidence must be between 0 and 1")
        return v
