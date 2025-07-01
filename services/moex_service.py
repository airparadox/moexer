import logging
import requests
import pandas as pd
import apimoex
from datetime import datetime, timedelta
from typing import Optional
from functools import lru_cache
from utils.helpers import retry_on_failure, APIError
from config import settings

logger = logging.getLogger(__name__)

class MOEXService:
    """Сервис для работы с данными MOEX"""
    
    @lru_cache(maxsize=128)
    @retry_on_failure(max_retries=settings.max_retries)
    def get_ticker_data(self, ticker: str, days_back: Optional[int] = None) -> pd.DataFrame:
        """
        Получает исторические данные по тикеру с MOEX
        
        Args:
            ticker: Тикер для получения данных
            days_back: Количество дней назад (по умолчанию из настроек)
            
        Returns:
            DataFrame с историческими данными
            
        Raises:
            APIError: При ошибках получения данных
        """
        try:
            days = days_back or settings.moex_days_lookback
            end = datetime.now()
            start = end - timedelta(days=days)
            
            with requests.Session() as session:
                data = apimoex.get_board_history(
                    session, ticker,
                    start=start.strftime('%Y-%m-%d'),
                    end=end.strftime('%Y-%m-%d')
                )
                
                if not data:
                    raise ValueError(f"No data available for ticker {ticker}")
                
                df = pd.DataFrame(data)[['TRADEDATE', 'CLOSE', 'VOLUME', 'VALUE']]
                return df
                
        except Exception as e:
            logger.error(f"MOEX error for {ticker}: {e}")
            raise APIError(f"Failed to get MOEX data for {ticker}: {e}")
    
    def get_recent_data(self, ticker: str, days: int = 20) -> str:
        """
        Получает данные за последние N дней в строковом формате
        
        Args:
            ticker: Тикер
            days: Количество последних дней
            
        Returns:
            Строковое представление данных
        """
        try:
            df = self.get_ticker_data(ticker)
            recent_data = df.tail(days)
            return recent_data.to_string(index=False)
        except Exception as e:
            logger.error(f"Failed to get recent data for {ticker}: {e}")
            return "Ошибка получения данных"