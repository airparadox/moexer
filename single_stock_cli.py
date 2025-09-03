import argparse
import logging

from analysis import predict_stock_direction, evaluate_prediction
from utils.logging_config import setup_logging

setup_logging()
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Single stock speculation tool")
    subparsers = parser.add_subparsers(dest="command", required=True)

    predict_parser = subparsers.add_parser("predict", help="Сделать прогноз")
    predict_parser.add_argument("ticker", help="Тикер акции")

    evaluate_parser = subparsers.add_parser("evaluate", help="Оценить прогноз")
    evaluate_parser.add_argument("ticker", help="Тикер акции")

    args = parser.parse_args()

    if args.command == "predict":
        result = predict_stock_direction(args.ticker)
        print(
            f"Прогноз для {result['ticker']}: "
            f"{'упадёт' if result['prediction']=='down' else 'не упадёт'}, "
            f"цена {result['reference_price']}"
        )
    elif args.command == "evaluate":
        result = evaluate_prediction(args.ticker)
        print(
            f"Результат для {result['ticker']}: "
            f"{'верно' if result['was_correct'] else 'неверно'}, "
            f"фактическая цена {result['actual_price']}"
        )
    else:
        logger.error("Неизвестная команда")


if __name__ == "__main__":
    main()
