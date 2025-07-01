from typing_extensions import TypedDict
from pydantic import BaseModel, validator
from typing import Dict, List, Optional
from dataclasses import dataclass

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
        if v <= 0:
            raise ValueError('Quantity must be positive')
        return v

class Portfolio(BaseModel):
    positions: List[PortfolioPosition]
    
    @classmethod
    def from_dict(cls, data: Dict[str, int]):
        positions = [PortfolioPosition(ticker=k, quantity=v) for k, v in data.items()]
        return cls(positions=positions)

@dataclass
class AnalysisResult:
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