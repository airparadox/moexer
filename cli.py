import argparse
import asyncio
import json
import logging
from datetime import datetime

from models import RiskProfile
from analysis import analyze_portfolio_async
from reports import (
    print_analysis_results,
    save_recommendations_to_db,
    save_full_report,
    save_html_report,
)
from utils import log_performance_summary
from utils.logging_config import setup_logging

setup_logging()
logger = logging.getLogger(__name__)


def load_portfolio_from_file(file_path: str) -> dict:
    """Загружает портфель из JSON-файла."""
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def parse_args():
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
    return parser.parse_args()


def main():
    args = parse_args()
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

    save_recommendations_to_db(results)
    print_analysis_results(results)

    print("\n" + "=" * 60)
    print("📊 ОТЧЕТ О ПРОИЗВОДИТЕЛЬНОСТИ")
    print("=" * 60)
    log_performance_summary()

    report_path = save_full_report(results, start_time)
    html_report_path = save_html_report(results, start_time)
    print(f"\n💾 Отчет сохранен в {report_path}")
    print(f"🌐 HTML-отчет сохранен в {html_report_path}")


if __name__ == "__main__":
    main()
