import logging

from models import Portfolio
from analyzers import PortfolioAnalyzer, RebalancingAnalyzer, AsyncPortfolioAnalyzer
from utils import calculate_portfolio_value

logger = logging.getLogger(__name__)


def analyze_portfolio_improved(portfolio_dict: dict) -> dict:
    """
    Улучшенная функция анализа портфеля с использованием новой архитектуры

    Args:
        portfolio_dict: Словарь с портфелем {ticker: quantity}

    Returns:
        Словарь с результатами анализа и рекомендациями
    """
    try:
        portfolio = Portfolio.from_dict(portfolio_dict)

        portfolio_analyzer = PortfolioAnalyzer()
        rebalancing_analyzer = RebalancingAnalyzer()

        logger.info("Начинаем анализ портфеля...")
        analysis_results = portfolio_analyzer.analyze_portfolio(portfolio)

        rebalancing_suggestions = rebalancing_analyzer.suggest_rebalancing(analysis_results, portfolio)
        portfolio_summary = rebalancing_analyzer.get_portfolio_summary(analysis_results, portfolio)

        total_value = calculate_portfolio_value(
            portfolio,
            portfolio_analyzer.moex_service.get_latest_price,
        )
        portfolio_summary["total_value"] = total_value

        results = {
            "analysis_results": {},
            "rebalancing_suggestions": rebalancing_suggestions,
            "portfolio_summary": portfolio_summary,
        }

        for ticker, result in analysis_results.items():
            results["analysis_results"][ticker] = {
                "quantity": next(pos.quantity for pos in portfolio.positions if pos.ticker == ticker),
                "recommendation": result.recommendation,
                "confidence": result.confidence,
                "decision": result.analysis_data.get("final_decision", "Нет данных"),
                "details": {
                    "market_news": result.analysis_data.get("market_news", ""),
                    "company_news": result.analysis_data.get("semantic", ""),
                    "technical_analysis": result.analysis_data.get("moex_analysis", ""),
                    "financial_data": result.analysis_data.get("ifrs_data", ""),
                    "pmpt": result.analysis_data.get("pmpt", {}),
                },
            }

        return results

    except Exception as e:
        logger.error(f"Ошибка при анализе портфеля: {e}")
        return {
            "error": str(e),
            "analysis_results": {},
            "rebalancing_suggestions": {},
            "portfolio_summary": {"error": "Ошибка анализа"},
        }


async def analyze_portfolio_async(portfolio_dict: dict) -> dict:
    """Асинхронный анализ портфеля с параллельной обработкой тикеров."""
    try:
        portfolio = Portfolio.from_dict(portfolio_dict)
        portfolio_analyzer = AsyncPortfolioAnalyzer()
        rebalancing_analyzer = RebalancingAnalyzer()

        logger.info("Начинаем асинхронный анализ портфеля...")
        analysis_results = await portfolio_analyzer.analyze_portfolio_async(portfolio)

        rebalancing_suggestions = rebalancing_analyzer.suggest_rebalancing(analysis_results, portfolio)
        portfolio_summary = rebalancing_analyzer.get_portfolio_summary(analysis_results, portfolio)

        total_value = calculate_portfolio_value(
            portfolio,
            portfolio_analyzer.moex_service.get_latest_price,
        )
        portfolio_summary["total_value"] = total_value

        results = {
            "analysis_results": {},
            "rebalancing_suggestions": rebalancing_suggestions,
            "portfolio_summary": portfolio_summary,
        }

        for ticker, result in analysis_results.items():
            results["analysis_results"][ticker] = {
                "quantity": next(pos.quantity for pos in portfolio.positions if pos.ticker == ticker),
                "recommendation": result.recommendation,
                "confidence": result.confidence,
                "decision": result.analysis_data.get("final_decision", "Нет данных"),
                "details": {
                    "market_news": result.analysis_data.get("market_news", ""),
                    "company_news": result.analysis_data.get("semantic", ""),
                    "technical_analysis": result.analysis_data.get("moex_analysis", ""),
                    "financial_data": result.analysis_data.get("ifrs_data", ""),
                    "pmpt": result.analysis_data.get("pmpt", {}),
                },
            }

        return results

    except Exception as e:
        logger.error(f"Ошибка при асинхронном анализе портфеля: {e}")
        return {
            "error": str(e),
            "analysis_results": {},
            "rebalancing_suggestions": {},
            "portfolio_summary": {"error": "Ошибка анализа"},
        }
