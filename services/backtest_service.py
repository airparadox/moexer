from datetime import timedelta
from typing import Dict

import pandas as pd

from .db_service import RecommendationDB
from .moex_service import MOEXService


class BacktestService:
    """Сервис для оценки качества рекомендаций."""

    def __init__(self, db_path: str = "recommendations.db") -> None:
        self.db = RecommendationDB(db_path)
        self.moex_service = MOEXService()

    def run_backtest(self, holding_period: int = 5) -> Dict[str, float]:
        """Проводит бэктест рекомендаций.

        Args:
            holding_period: количество дней удержания позиции

        Returns:
            Словарь с метриками бэктеста
        """
        records = self.db.fetch_all()
        if not records:
            return {"total": 0, "correct": 0, "avg_return": 0.0}

        total_return = 0.0
        correct = 0

        for rec in records:
            try:
                df: pd.DataFrame = self.moex_service.get_ticker_data(
                    rec.ticker, days_back=holding_period + 10
                )
                df = df.sort_values("TRADEDATE")
                target_date = rec.timestamp.date() + timedelta(days=holding_period)
                future = df[df["TRADEDATE"] >= pd.Timestamp(target_date)]
                if future.empty:
                    continue
                future_price = float(future.iloc[0]["CLOSE"])
                ret = (future_price - rec.price) / rec.price
                total_return += ret

                if rec.recommendation == "КУПИТЬ" and ret > 0:
                    correct += 1
                elif rec.recommendation == "ПРОДАВАТЬ" and ret < 0:
                    correct += 1
                elif rec.recommendation == "ДЕРЖАТЬ" and abs(ret) < 0.01:
                    correct += 1
            except Exception:
                continue

        return {
            "total": len(records),
            "correct": correct,
            "avg_return": total_return / len(records),
        }
