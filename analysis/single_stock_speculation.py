from __future__ import annotations

import json
import logging
from datetime import datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo

from services.moex_service import MOEXService

logger = logging.getLogger(__name__)

# Файл для хранения сделанных прогнозов
PREDICTIONS_FILE = Path("speculation_predictions.json")


def _load_predictions() -> list[dict]:
    """Загружает сохранённые прогнозы из файла."""
    if PREDICTIONS_FILE.exists():
        try:
            return json.loads(PREDICTIONS_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            logger.warning("Файл прогнозов повреждён, создаём новый")
            return []
    return []


def _save_predictions(predictions: list[dict]) -> None:
    PREDICTIONS_FILE.write_text(
        json.dumps(predictions, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def predict_stock_direction(ticker: str) -> dict:
    """Делает прогноз по отдельной акции: упадёт цена или нет.

    Прогноз должен быть выполнен до 12:00 МСК. Используется простое
    правило: если текущая цена закрытия выше среднего за 5 дней,
    прогнозируется падение.
    """
    now = datetime.now(ZoneInfo("Europe/Moscow"))
    if now.time() > time(12, 0):
        raise RuntimeError("Прогноз должен быть сделан до 12:00 МСК")

    moex = MOEXService()
    df = moex.get_ticker_data(ticker)
    last_close = float(df["CLOSE"].iloc[-1])
    ma5 = float(df["CLOSE"].tail(5).mean())
    prediction = "down" if last_close > ma5 else "not_down"

    record = {
        "ticker": ticker.upper(),
        "prediction": prediction,
        "reference_price": last_close,
        "timestamp": now.isoformat(),
    }
    predictions = _load_predictions()
    predictions.append(record)
    _save_predictions(predictions)
    logger.info("Сохранён прогноз для %s: %s", ticker, prediction)
    return record


def evaluate_prediction(ticker: str) -> dict:
    """Оценивает ранее сделанный прогноз.

    Оценка возможна только после 19:09 МСК. Сравнивает реальную цену
    закрытия с ценой, использованной в прогнозе.
    """
    now = datetime.now(ZoneInfo("Europe/Moscow"))
    if now.time() < time(19, 9):
        raise RuntimeError("Оценку можно проводить после 19:09 МСК")

    predictions = _load_predictions()
    prediction = next(
        (p for p in reversed(predictions) if p["ticker"] == ticker.upper()),
        None,
    )
    if prediction is None:
        raise RuntimeError("Прогноз для указанного тикера не найден")

    moex = MOEXService()
    df = moex.get_ticker_data(ticker, days_back=1)
    actual_price = float(df["CLOSE"].iloc[-1])
    price_fell = actual_price < prediction["reference_price"]
    was_correct = (prediction["prediction"] == "down") == price_fell

    prediction.update({
        "actual_price": actual_price,
        "was_correct": was_correct,
    })
    _save_predictions(predictions)
    logger.info(
        "Оценка прогноза для %s: %s", ticker, "верный" if was_correct else "неверный"
    )
    return {
        "ticker": ticker.upper(),
        "predicted": prediction["prediction"],
        "actual_price": actual_price,
        "was_correct": was_correct,
    }
