import logging
from typing import Dict, Callable
from langsmith import traceable
from models.state import AnalysisResult, Portfolio, RiskProfile
from services.moex_service import MOEXService

logger = logging.getLogger(__name__)

class RebalancingAnalyzer:
    """Анализатор для предложений по ребалансировке портфеля"""
    
    BROKER_FEE = 0.0006  # 0.06%
    TAX_RATE = 0.15  # 15%

    def __init__(self, price_getter: Callable[[str], float] | None = None):
        self.price_getter = price_getter or MOEXService().get_latest_price

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

        # Сначала продаем рекомендации "ПРОДАВАТЬ"
        for ticker, result in analysis_results.items():
            if result.recommendation != "ПРОДАВАТЬ":
                continue
            position = portfolio.get_position(ticker)
            if not position or position.quantity <= 0:
                excluded_tickers.add(ticker)
                continue
            qty = position.quantity
            try:
                price = self.price_getter(ticker)
            except Exception as e:
                logger.error(f"Failed to get price for {ticker}: {e}")
                excluded_tickers.add(ticker)
                continue

            proceeds = price * qty * (1 - self.BROKER_FEE)
            proceeds_after_tax = proceeds * (1 - self.TAX_RATE)
            cash += proceeds_after_tax
            rebalancing_suggestions[ticker] = f"Продать {qty}"

        # Затем покупаем согласно рекомендациям "КУПИТЬ"
        buy_prices: Dict[str, float] = {}
        for ticker, result in analysis_results.items():
            if result.recommendation != "КУПИТЬ":
                continue
            try:
                buy_prices[ticker] = self.price_getter(ticker)
            except Exception as e:
                logger.error(f"Failed to get price for {ticker}: {e}")
                excluded_tickers.add(ticker)

        buy_tickers = list(buy_prices.keys())
        quantities: Dict[str, int] = {}

        while buy_tickers:
            min_price = min(buy_prices[t] * (1 + self.BROKER_FEE) for t in buy_tickers)
            if cash < min_price:
                break
            cash_per_ticker = cash / len(buy_tickers)
            to_remove = []
            for ticker in buy_tickers:
                price = buy_prices[ticker]
                qty = int(cash_per_ticker / (price * (1 + self.BROKER_FEE)))
                if qty > 0:
                    cost = qty * price * (1 + self.BROKER_FEE)
                    cash -= cost
                    quantities[ticker] = quantities.get(ticker, 0) + qty
                else:
                    to_remove.append(ticker)
            if not to_remove:
                break
            for ticker in to_remove:
                buy_tickers.remove(ticker)
                excluded_tickers.add(ticker)

        for ticker, price in sorted(buy_prices.items(), key=lambda x: x[1]):
            if ticker not in quantities:
                continue
            while cash >= price * (1 + self.BROKER_FEE):
                qty = int(cash / (price * (1 + self.BROKER_FEE)))
                cost = qty * price * (1 + self.BROKER_FEE)
                cash -= cost
                quantities[ticker] += qty

        for ticker, qty in quantities.items():
            rebalancing_suggestions[ticker] = f"Купить {qty}"

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