from typing_extensions import TypedDict
from pydantic import BaseModel, validator
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum

class State(TypedDict):
    ticker: str
    quantity: int
    news: str
    semantic: str
    moex_data: str
    moex_data_analysis: str
    ifrs_data: str
    final_data: str
    market_news: str
    risk_profile: str

class PortfolioPosition(BaseModel):
    ticker: str
    quantity: int
    
    @validator('ticker')
    def validate_ticker(cls, v):
        if not v or len(v) < 3:
            raise ValueError('Ticker must be at least 3 characters')
        return v.upper()
    
    @validator('quantity')
    def validate_quantity(cls, v):
        if v < 0:
            raise ValueError('Quantity must be non-negative')
        return v

class RiskProfile(str, Enum):
    CONSERVATIVE = "консервативный"
    BALANCED = "сбалансированный"
    AGGRESSIVE = "агрессивный"


class Portfolio(BaseModel):
    positions: List[PortfolioPosition]
    cash_rub: float = 0.0
    risk_profile: RiskProfile = RiskProfile.BALANCED

    @classmethod
    def from_dict(cls, data: Dict[str, int]):
        cash = float(data.get("RUB", 0))
        risk_profile = data.get("risk_profile", RiskProfile.BALANCED)
        # Приводим строковый профиль к Enum, если необходимо
        if isinstance(risk_profile, str):
            try:
                risk_profile = RiskProfile(risk_profile)
            except ValueError:
                raise ValueError(
                    f"Risk profile must be one of {[p.value for p in RiskProfile]}"
                )
        positions = [
            PortfolioPosition(ticker=k, quantity=v)
            for k, v in data.items()
            if k not in {"RUB", "risk_profile"}
        ]
        return cls(positions=positions, cash_rub=cash, risk_profile=risk_profile)

    def get_tickers(self) -> List[str]:
        return [pos.ticker for pos in self.positions]

    def get_position(self, ticker: str) -> Optional[PortfolioPosition]:
        for pos in self.positions:
            if pos.ticker == ticker:
                return pos
        return None

class AnalysisResult(BaseModel):
    """
    Результат анализа тикера.
    
    Attributes:
        ticker: Тикер инструмента
        recommendation: Рекомендация (КУПИТЬ/ДЕРЖАТЬ/ПРОДАВАТЬ)
        confidence: Уровень уверенности (0-1)
        analysis_data: Детальные данные анализа
    """
    ticker: str
    recommendation: str
    confidence: float
    analysis_data: Dict[str, str]

    @validator('confidence')
    def validate_confidence(cls, v):
        if not 0.0 <= v <= 1.0:
            raise ValueError('Confidence must be between 0 and 1')
        return v
