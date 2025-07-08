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
        cash = portfolio.cash_rub
        total_positions = len(analysis_results)
        
        if total_positions == 0:
            return rebalancing_suggestions
        
        # Подсчитываем рекомендации
        recommendations_count = {
            "КУПИТЬ": 0,
            "ПРОДАВАТЬ": 0,
            "ДЕРЖАТЬ": 0
        }
        
        for result in analysis_results.values():
            recommendations_count[result.recommendation] += 1
        
        # Генерируем предложения
        # Сначала продаем рекомендации "ПРОДАВАТЬ"
        for ticker, result in analysis_results.items():
            if result.recommendation != "ПРОДАВАТЬ":
                continue
            position = portfolio.get_position(ticker)
            if not position or position.quantity <= 0:
                rebalancing_suggestions[ticker] = "Позиция отсутствует"
                continue
            qty = position.quantity
            try:
                price = self.price_getter(ticker)
            except Exception as e:
                logger.error(f"Failed to get price for {ticker}: {e}")
                rebalancing_suggestions[ticker] = "Цена недоступна"
                continue

            proceeds = price * qty * (1 - self.BROKER_FEE)
            proceeds_after_tax = proceeds * (1 - self.TAX_RATE)
            cash += proceeds_after_tax
            rebalancing_suggestions[ticker] = f"Продать {qty}"

        # Затем покупаем согласно рекомендациям "КУПИТЬ"
        buy_tickers = [t for t, r in analysis_results.items() if r.recommendation == "КУПИТЬ"]
        buy_count = len(buy_tickers)
        for ticker in buy_tickers:
            try:
                price = self.price_getter(ticker)
            except Exception as e:
                logger.error(f"Failed to get price for {ticker}: {e}")
                rebalancing_suggestions[ticker] = "Цена недоступна"
                continue

            cash_per_ticker = cash / buy_count if buy_count else 0
            qty = int(cash_per_ticker / (price * (1 + self.BROKER_FEE)))
            if qty > 0:
                cost = qty * price * (1 + self.BROKER_FEE)
                cash -= cost
                rebalancing_suggestions[ticker] = f"Купить {qty}"
            else:
                rebalancing_suggestions[ticker] = "Недостаточно средств"

        # Для остальных "ДЕРЖАТЬ"
        for ticker, result in analysis_results.items():
            if ticker not in rebalancing_suggestions:
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

        summary["portfolio_action"] = action

        summary["cash_rub"] = portfolio.cash_rub
        summary["risk_profile"] = portfolio.risk_profile.value
        return summary