import logging
import asyncio
from dotenv import load_dotenv

from models import Portfolio
from analyzers import PortfolioAnalyzer, RebalancingAnalyzer, AsyncPortfolioAnalyzer
from utils import log_performance_summary

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Загружаем переменные окружения
load_dotenv()

def analyze_portfolio_improved(portfolio_dict: dict) -> dict:
    """
    Улучшенная функция анализа портфеля с использованием новой архитектуры
    
    Args:
        portfolio_dict: Словарь с портфелем {ticker: quantity}
        
    Returns:
        Словарь с результатами анализа и рекомендациями
    """
    try:
        # Создаем объект портфеля с валидацией
        portfolio = Portfolio.from_dict(portfolio_dict)
        
        # Инициализируем анализаторы
        portfolio_analyzer = PortfolioAnalyzer()
        rebalancing_analyzer = RebalancingAnalyzer()
        
        # Выполняем анализ портфеля
        logger.info("Начинаем анализ портфеля...")
        analysis_results = portfolio_analyzer.analyze_portfolio(portfolio)
        
        # Получаем рекомендации по ребалансировке
        rebalancing_suggestions = rebalancing_analyzer.suggest_rebalancing(analysis_results)
        
        # Получаем общую сводку
        portfolio_summary = rebalancing_analyzer.get_portfolio_summary(analysis_results)
        
        # Формируем результат
        results = {
            "analysis_results": {},
            "rebalancing_suggestions": rebalancing_suggestions,
            "portfolio_summary": portfolio_summary
        }
        
        # Преобразуем результаты анализа в удобный формат
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
                    "financial_data": result.analysis_data.get("ifrs_data", "")
                }
            }
        
        return results
        
    except Exception as e:
        logger.error(f"Ошибка при анализе портфеля: {e}")
        return {
            "error": str(e),
            "analysis_results": {},
            "rebalancing_suggestions": {},
            "portfolio_summary": {"error": "Ошибка анализа"}
        }


async def analyze_portfolio_async(portfolio_dict: dict) -> dict:
    """Асинхронный анализ портфеля с параллельной обработкой тикеров."""
    try:
        portfolio = Portfolio.from_dict(portfolio_dict)
        portfolio_analyzer = AsyncPortfolioAnalyzer()
        rebalancing_analyzer = RebalancingAnalyzer()

        logger.info("Начинаем асинхронный анализ портфеля...")
        analysis_results = await portfolio_analyzer.analyze_portfolio_async(portfolio)

        rebalancing_suggestions = rebalancing_analyzer.suggest_rebalancing(analysis_results)
        portfolio_summary = rebalancing_analyzer.get_portfolio_summary(analysis_results)

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

def print_analysis_results(results: dict):
    """Выводит результаты анализа в удобном формате"""
    if "error" in results:
        print(f"❌ Ошибка: {results['error']}")
        return
    
    # Выводим общую сводку по портфелю
    summary = results["portfolio_summary"]
    print("\n" + "="*60)
    print("📊 СВОДКА ПО ПОРТФЕЛЮ")
    print("="*60)
    print(f"Всего позиций: {summary['total_positions']}")
    print(f"К покупке: {summary['buy_recommendations']}")
    print(f"Держать: {summary['hold_recommendations']}")
    print(f"К продаже: {summary['sell_recommendations']}")
    print(f"Средняя уверенность: {summary['average_confidence']:.2f}")
    print(f"Общая стратегия: {summary['portfolio_action']}")
    
    # Выводим детальные результаты по каждому тикеру
    print("\n" + "="*60)
    print("📈 ДЕТАЛЬНЫЙ АНАЛИЗ ПО ТИКЕРАМ")
    print("="*60)
    
    for ticker, data in results["analysis_results"].items():
        print(f"\n🏢 {ticker}")
        print(f"   Количество: {data['quantity']}")
        print(f"   Рекомендация: {data['recommendation']} (уверенность: {data['confidence']:.2f})")
        print(f"   Решение: {data['decision']}...")
        print(f"   Ребалансировка: {results['rebalancing_suggestions'][ticker]}")


if __name__ == "__main__":
    # Тестовый портфель
    portfolio = {
        'MGNT': 13,
        'TRNFP': 111,
        'UNAC': 100,
        'SBER': 100
    }
    
    print("🚀 Запуск улучшенного анализа портфеля (async)...")
    print(f"Анализируемый портфель: {portfolio}")

    # Выполняем анализ с новой архитектурой асинхронно
    results = asyncio.run(analyze_portfolio_async(portfolio))
    
    # Выводим результаты
    print_analysis_results(results)
    
    # Выводим сводку производительности
    print("\n" + "="*60)
    print("📊 ОТЧЕТ О ПРОИЗВОДИТЕЛЬНОСТИ")
    print("="*60)
    log_performance_summary()
