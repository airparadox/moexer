import logging
from datetime import datetime, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Optional

import apimoex
import pandas as pd
import requests

from utils.helpers import APIError, retry_on_failure
from config import settings

logger = logging.getLogger(__name__)

class MOEXService:
    """Сервис для работы с данными MOEX"""

    @lru_cache(maxsize=1)
    def _load_dividend_calendar(self) -> pd.DataFrame:
        """Загружает календарь дивидендных отсечек."""
        path = Path(__file__).resolve().parent.parent / "finance" / "dividend.txt"
        try:
            df = pd.read_csv(
                path,
                sep=r"\s+",
                engine="python",
                encoding="utf-8",
                names=["dDate", "sTicker"],
                header=0,
            )
            df["dDate"] = pd.to_datetime(df["dDate"], format="%d.%m.%Y", errors="coerce")
            df["sTicker"] = df["sTicker"].str.strip().str.upper()
            return df
        except Exception as e:
            logger.error(f"Failed to load dividend calendar: {e}")
            return pd.DataFrame(columns=["dDate", "sTicker"])

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
                df['TRADEDATE'] = pd.to_datetime(df['TRADEDATE'])

                # Помечаем даты дивидендных отсечек
                calendar = self._load_dividend_calendar()
                divs = calendar[calendar['sTicker'] == ticker.upper()][['dDate']]
                divs = divs.rename(columns={'dDate': 'TRADEDATE'})
                divs['IS_DIVIDEND_DAY'] = True
                df = df.merge(divs, on='TRADEDATE', how='left')
                df['IS_DIVIDEND_DAY'] = (
                    df['IS_DIVIDEND_DAY']
                    .astype('boolean')
                    .fillna(False)
                    .astype(bool)
                )

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

    @retry_on_failure(max_retries=settings.max_retries)
    def get_latest_price(self, ticker: str) -> float:
        """Возвращает последнюю цену закрытия по тикеру."""
        try:
            df = self.get_ticker_data(ticker, days_back=5)
            return float(df['CLOSE'].iloc[-1])
        except Exception as e:
            logger.error(f"Failed to get latest price for {ticker}: {e}")
            raise APIError(f"Failed to get latest price for {ticker}: {e}")

    @retry_on_failure(max_retries=settings.max_retries)
    def get_latest_prices(self, tickers: list[str]) -> pd.DataFrame:
        """Возвращает последние цены закрытия для списка тикеров."""
        try:
            url = (
                "https://iss.moex.com/iss/engines/stock/markets/shares/securities.json"
            )
            params = {"securities": ",".join(tickers)}
            with requests.Session() as session:
                resp = session.get(url, params=params)
                resp.raise_for_status()
                data = resp.json()
            sec = data.get("securities", {})
            if not sec:
                raise ValueError("No data returned")

            df = pd.DataFrame(sec["data"], columns=sec["columns"])

            price_columns = [
                "PREVCLOSE",
                "PREVPRICE",
                "PREVADMITTEDQUOTE",
                "CLOSEPRICE",
                "LAST",
            ]
            for col in price_columns:
                if col in df.columns:
                    df = df[["SECID", col]].rename(
                        columns={"SECID": "ticker", col: "price"}
                    )
                    break
            else:
                raise KeyError("No known price column found")

            df["ticker"] = df["ticker"].str.upper()
            return df.set_index("ticker")
        except Exception as e:
            logger.error(f"Failed to get prices for {tickers}: {e}")
            raise APIError(f"Failed to get prices for {tickers}: {e}")

    def get_returns(self, ticker: str, days_back: Optional[int] = None) -> list[float]:
        """Возвращает ряд доходностей по закрытиям."""
        try:
            df = self.get_ticker_data(ticker, days_back=days_back)
            returns = df['CLOSE'].pct_change().dropna().tolist()
            return [float(r) for r in returns]
        except Exception as e:
            logger.error(f"Failed to get returns for {ticker}: {e}")
            raise APIError(f"Failed to get returns for {ticker}: {e}")
