import logging
from typing import Dict
from langsmith import traceable
from models.state import AnalysisResult

logger = logging.getLogger(__name__)

class RebalancingAnalyzer:
    """Анализатор для предложений по ребалансировке портфеля"""
    
    @traceable
    def suggest_rebalancing(self, analysis_results: Dict[str, AnalysisResult]) -> Dict[str, str]:
        """
        Предлагает стратегию ребалансировки на основе анализа
        
        Args:
            analysis_results: Результаты анализа по каждому тикеру
            
        Returns:
            Словарь с рекомендациями по ребалансировке
        """
        rebalancing_suggestions = {}
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
        for ticker, result in analysis_results.items():
            confidence_text = self._get_confidence_text(result.confidence)
            
            if result.recommendation == "КУПИТЬ":
                suggestion = f"Увеличить позицию. {confidence_text}"
            elif result.recommendation == "ПРОДАВАТЬ":
                suggestion = f"Уменьшить позицию. {confidence_text}"
            else:  # ДЕРЖАТЬ
                suggestion = f"Сохранить текущую позицию. {confidence_text}"
            
            # Добавляем контекст о портфеле
            if recommendations_count["ПРОДАВАТЬ"] > total_positions // 2:
                suggestion += " Рассмотрите общее снижение рисков портфеля."
            elif recommendations_count["КУПИТЬ"] > total_positions // 2:
                suggestion += " Хорошие возможности для роста портфеля."
            
            rebalancing_suggestions[ticker] = suggestion
        
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
    
    def get_portfolio_summary(self, analysis_results: Dict[str, AnalysisResult]) -> Dict[str, any]:
        """
        Создает общую сводку по портфелю
        
        Args:
            analysis_results: Результаты анализа
            
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
        
        # Общая рекомендация для портфеля
        if summary["sell_recommendations"] > summary["total_positions"] // 2:
            summary["portfolio_action"] = "Рассмотрите снижение рисков"
        elif summary["buy_recommendations"] > summary["total_positions"] // 2:
            summary["portfolio_action"] = "Хорошие возможности для роста"
        else:
            summary["portfolio_action"] = "Сбалансированный подход"
        
        return summary