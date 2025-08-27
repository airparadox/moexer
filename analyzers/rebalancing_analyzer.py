import logging
from typing import Callable, Dict, List

import pandas as pd
from langsmith import traceable

from models.state import AnalysisResult, Portfolio, RiskProfile
from services.moex_service import MOEXService

logger = logging.getLogger(__name__)

class RebalancingAnalyzer:
    """Анализатор для предложений по ребалансировке портфеля"""
    
    BROKER_FEE = 0.0006  # 0.06%
    TAX_RATE = 0.15  # 15%

    def __init__(self, price_getter: Callable[[List[str]], pd.DataFrame] | None = None):
        """Initialize analyzer.

        Args:
            price_getter: Callable that accepts list of tickers and returns
                DataFrame with index as tickers and column ``price``.
        """
        self.price_getter = price_getter or MOEXService().get_latest_prices

    @traceable
    def suggest_rebalancing(
        self,
        analysis_results: Dict[str, AnalysisResult],
        portfolio: Portfolio,
    ) -> Dict[str, str]:
        """
        Предлагает стратегию ребалансировки на основе анализа

        Args:
            analysis_results: Результаты анализа по каждому тикеру
            portfolio: Портфель с позициями и наличными в рублях

        Returns:
            Словарь с рекомендациями по ребалансировке
        """
        rebalancing_suggestions: Dict[str, str] = {}
        excluded_tickers: set[str] = set()
        cash = portfolio.cash_rub

        if not analysis_results:
            return rebalancing_suggestions

        tickers = list(analysis_results.keys())
        try:
            prices_df = self.price_getter(tickers)
        except Exception as e:
            logger.error(f"Failed to get prices: {e}")
            return rebalancing_suggestions

        prices_df = prices_df.copy()
        if "price" not in prices_df.columns:
            raise ValueError("Price DataFrame must contain 'price' column")

        positions_df = pd.DataFrame(
            [(p.ticker, p.quantity) for p in portfolio.positions],
            columns=["ticker", "quantity"],
        ).set_index("ticker")

        # ----- Sell recommendations -----
        sell_tickers = [
            t for t, r in analysis_results.items() if r.recommendation == "ПРОДАВАТЬ"
        ]
        sell_df = positions_df.reindex(sell_tickers)
        missing_positions = sell_df[sell_df["quantity"].isna()].index
        excluded_tickers.update(missing_positions)
        sell_df = sell_df.dropna()
        zero_qty = sell_df[sell_df["quantity"] <= 0].index
        excluded_tickers.update(zero_qty)
        sell_df = sell_df[sell_df["quantity"] > 0]
        sell_df = sell_df.join(prices_df[["price"]], how="left")
        missing_sell_prices = sell_df[sell_df["price"].isna()].index
        excluded_tickers.update(missing_sell_prices)
        sell_df = sell_df.dropna(subset=["price"])

        if not sell_df.empty:
            proceeds = (
                sell_df["price"]
                * sell_df["quantity"]
                * (1 - self.BROKER_FEE)
                * (1 - self.TAX_RATE)
            )
            cash += proceeds.sum()
            for ticker, qty in sell_df["quantity"].items():
                rebalancing_suggestions[ticker] = f"Продать {int(qty)}"

        # ----- Buy recommendations -----
        buy_tickers = [
            t for t, r in analysis_results.items() if r.recommendation == "КУПИТЬ"
        ]
        buy_df = prices_df.reindex(buy_tickers).dropna(subset=["price"])
        missing_buy_prices = set(buy_tickers) - set(buy_df.index)
        excluded_tickers.update(missing_buy_prices)

        if not buy_df.empty and cash > 0:
            adjusted_prices = buy_df["price"] * (1 + self.BROKER_FEE)
            base_quantities = (cash / len(buy_df) / adjusted_prices).astype(int)
            spent = (base_quantities * adjusted_prices).sum()
            cash_remaining = cash - spent

            additional = pd.Series(0, index=buy_df.index, dtype=int)
            for ticker, price in adjusted_prices.sort_values().items():
                if cash_remaining < price:
                    break
                qty = int(cash_remaining / price)
                additional[ticker] = qty
                cash_remaining -= qty * price

            quantities = (base_quantities + additional).astype(int)
            cash = cash_remaining

            for ticker, qty in quantities[quantities > 0].items():
                rebalancing_suggestions[ticker] = f"Купить {int(qty)}"

        for ticker, result in analysis_results.items():
            if ticker not in rebalancing_suggestions and ticker not in excluded_tickers:
                rebalancing_suggestions[ticker] = "Держать"

        rebalancing_suggestions["RUB"] = f"Остаток {int(round(cash))}"

        return rebalancing_suggestions
    
    def _get_confidence_text(self, confidence: float) -> str:
        """Преобразует уровень уверенности в текстовое описание"""
        if confidence >= 0.8:
            return "Высокая уверенность"
        elif confidence >= 0.6:
            return "Средняя уверенность"
        elif confidence >= 0.4:
            return "Низкая уверенность"
        else:
            return "Данные неполные"
    
    def get_portfolio_summary(
        self, analysis_results: Dict[str, AnalysisResult], portfolio: Portfolio
    ) -> Dict[str, any]:
        """
        Создает общую сводку по портфелю
        
        Args:
            analysis_results: Результаты анализа
            portfolio: Портфель пользователя
            
        Returns:
            Словарь с общей статистикой портфеля
        """
        if not analysis_results:
            return {"error": "Нет данных для анализа"}
        
        recommendations = [result.recommendation for result in analysis_results.values()]
        confidences = [result.confidence for result in analysis_results.values()]
        
        summary = {
            "total_positions": len(analysis_results),
            "buy_recommendations": recommendations.count("КУПИТЬ"),
            "sell_recommendations": recommendations.count("ПРОДАВАТЬ"),
            "hold_recommendations": recommendations.count("ДЕРЖАТЬ"),
            "average_confidence": sum(confidences) / len(confidences) if confidences else 0,
            "high_confidence_count": sum(1 for c in confidences if c >= 0.8),
        }
        
        # Общая рекомендация для портфеля с учетом типа инвестирования
        if summary["sell_recommendations"] > summary["total_positions"] // 2:
            action = "Рассмотрите снижение рисков"
        elif summary["buy_recommendations"] > summary["total_positions"] // 2:
            action = "Хорошие возможности для роста"
        else:
            action = "Сбалансированный подход"

        if portfolio.risk_profile == RiskProfile.CONSERVATIVE:
            action += ". Поддерживайте осторожный подход"
        elif portfolio.risk_profile == RiskProfile.AGGRESSIVE:
            action += ". Допустимы более рисковые сделки"
        elif portfolio.risk_profile == RiskProfile.SPECULATIVE:
            action += ". Ребалансируйте портфель ежедневно или еженедельно"

        summary["portfolio_action"] = action

        summary["cash_rub"] = portfolio.cash_rub
        summary["risk_profile"] = portfolio.risk_profile.value
        return summary