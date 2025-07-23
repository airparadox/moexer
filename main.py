import logging
import asyncio
import json
import argparse
from dotenv import load_dotenv

from models import Portfolio, RiskProfile
from analyzers import PortfolioAnalyzer, RebalancingAnalyzer, AsyncPortfolioAnalyzer
from utils import (
    log_performance_summary,
    calculate_portfolio_value,
    get_performance_report,
)
from datetime import datetime
import os

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Загружаем переменные окружения
load_dotenv()

def load_portfolio_from_file(file_path: str) -> dict:
    """Загружает портфель из JSON-файла."""
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)

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
        rebalancing_suggestions = rebalancing_analyzer.suggest_rebalancing(analysis_results, portfolio)
        
        # Получаем общую сводку
        portfolio_summary = rebalancing_analyzer.get_portfolio_summary(analysis_results, portfolio)

        total_value = calculate_portfolio_value(
            portfolio,
            portfolio_analyzer.moex_service.get_latest_price,
        )
        portfolio_summary["total_value"] = total_value
        
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
                    "financial_data": result.analysis_data.get("ifrs_data", ""),
                    "pmpt": result.analysis_data.get("pmpt", {}),
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
    if 'risk_profile' in summary:
        print(f"Тип инвестора: {summary['risk_profile']}")
    if 'total_value' in summary:
        print(f"Стоимость портфеля: {summary['total_value']:.2f} руб.")
    if 'cash_rub' in summary:
        print(f"Свободные средства: {summary['cash_rub']:.2f} руб.")
    
    # Выводим детальные результаты по каждому тикеру
    print("\n" + "="*60)
    print("📈 ДЕТАЛЬНЫЙ АНАЛИЗ ПО ТИКЕРАМ")
    print("="*60)
    
    for ticker, data in results["analysis_results"].items():
        print(f"\n🏢 {ticker}")
        print(f"   Количество: {data['quantity']}")
        print(f"   Решение: {data['decision']}...")
        print(f"   Ребалансировка: {results['rebalancing_suggestions'][ticker]}")
        pmpt = data['details'].get('pmpt', {})
        if pmpt:
            print(
                f"   Downside risk: {pmpt.get('downside_risk', float('nan')):.4f}"
            )
            print(
                f"   Sortino ratio: {pmpt.get('sortino_ratio', float('nan')):.4f}"
            )
            print(
                f"   Omega ratio: {pmpt.get('omega_ratio', float('nan')):.4f}"
            )

    # Итоговая таблица действий
    print("\n" + "="*60)
    print("📋 ИТОГОВАЯ ТАБЛИЦА ДЕЙСТВИЙ")
    print("="*60)
    for ticker, action in results["rebalancing_suggestions"].items():
        print(f"{ticker:<6} {action}")


def generate_analysis_report(results: dict) -> str:
    """Формирует текстовый отчет по результатам анализа."""
    if "error" in results:
        return f"❌ Ошибка: {results['error']}"

    lines = []
    summary = results["portfolio_summary"]
    lines.append("=" * 60)
    lines.append("📊 СВОДКА ПО ПОРТФЕЛЮ")
    lines.append("=" * 60)
    lines.append(f"Всего позиций: {summary['total_positions']}")
    lines.append(f"К покупке: {summary['buy_recommendations']}")
    lines.append(f"Держать: {summary['hold_recommendations']}")
    lines.append(f"К продаже: {summary['sell_recommendations']}")
    lines.append(f"Средняя уверенность: {summary['average_confidence']:.2f}")
    lines.append(f"Общая стратегия: {summary['portfolio_action']}")
    if "risk_profile" in summary:
        lines.append(f"Тип инвестора: {summary['risk_profile']}")
    if "total_value" in summary:
        lines.append(f"Стоимость портфеля: {summary['total_value']:.2f} руб.")
    if "cash_rub" in summary:
        lines.append(f"Свободные средства: {summary['cash_rub']:.2f} руб.")

    lines.append("")
    lines.append("=" * 60)
    lines.append("📈 ДЕТАЛЬНЫЙ АНАЛИЗ ПО ТИКЕРАМ")
    lines.append("=" * 60)

    for ticker, data in results["analysis_results"].items():
        lines.append(f"\n🏢 {ticker}")
        lines.append(f"   Количество: {data['quantity']}")
        lines.append(f"   Решение: {data['decision']}...")
        lines.append(f"   Ребалансировка: {results['rebalancing_suggestions'][ticker]}")
        pmpt = data['details'].get('pmpt', {})
        if pmpt:
            lines.append(f"   Downside risk: {pmpt.get('downside_risk', float('nan')):.4f}")
            lines.append(f"   Sortino ratio: {pmpt.get('sortino_ratio', float('nan')):.4f}")
            lines.append(f"   Omega ratio: {pmpt.get('omega_ratio', float('nan')):.4f}")

    lines.append("")
    lines.append("=" * 60)
    lines.append("📋 ИТОГОВАЯ ТАБЛИЦА ДЕЙСТВИЙ")
    lines.append("=" * 60)
    for ticker, action in results["rebalancing_suggestions"].items():
        lines.append(f"{ticker:<6} {action}")

    return "\n".join(lines)


def save_full_report(results: dict, start_time: datetime) -> str:
    """Сохраняет полный отчет анализа и метрик в файл."""
    analysis_report = generate_analysis_report(results)
    performance_report = get_performance_report()
    full_report = (
        analysis_report
        + "\n\n=== ОТЧЕТ О ПРОИЗВОДИТЕЛЬНОСТИ ===\n"
        + performance_report
    )

    os.makedirs("reports", exist_ok=True)
    file_name = start_time.strftime("report_%Y%m%d_%H%M%S.txt")
    path = os.path.join("reports", file_name)
    with open(path, "w", encoding="utf-8") as f:
        f.write(full_report)
    return path

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Portfolio analyzer")
    parser.add_argument(
        "-f",
        "--file",
        default="portfolio.json",
        help="Путь к JSON-файлу с портфелем",
    )
    parser.add_argument(
        "-r",
        "--risk-profile",
        default=RiskProfile.BALANCED.value,
        choices=[p.value for p in RiskProfile],
        help="Тип инвестирования",
    )
    args = parser.parse_args()

    start_time = datetime.now()

    try:
        portfolio_data = load_portfolio_from_file(args.file)
        portfolio_data["risk_profile"] = args.risk_profile
    except Exception as e:
        logger.error(f"Ошибка чтения портфеля из файла: {e}")
        raise SystemExit(1)

    print("🚀 Запуск улучшенного анализа портфеля (async)...")
    print(f"Анализируемый портфель: {portfolio_data}")

    try:
        results = asyncio.run(analyze_portfolio_async(portfolio_data))
    except Exception as e:
        logger.error(f"Critical error during analysis: {e}")
        results = {
            "error": str(e),
            "analysis_results": {},
            "rebalancing_suggestions": {},
            "portfolio_summary": {"error": "Ошибка анализа"},
        }
    
    # Выводим результаты
    print_analysis_results(results)

    # Выводим сводку производительности
    print("\n" + "="*60)
    print("📊 ОТЧЕТ О ПРОИЗВОДИТЕЛЬНОСТИ")
    print("="*60)
    log_performance_summary()

    report_path = save_full_report(results, start_time)
    print(f"\n💾 Отчет сохранен в {report_path}")
