import pandas as pd
from datetime import datetime
from zoneinfo import ZoneInfo
from unittest.mock import patch
import importlib.util
from pathlib import Path
import sys
import types

dummy_service = types.ModuleType("services.moex_service")


class DummyMOEXService:
    def get_ticker_data(self, *args, **kwargs):  # pragma: no cover - replaced in tests
        raise NotImplementedError


dummy_service.MOEXService = DummyMOEXService
sys.modules["services.moex_service"] = dummy_service

spec = importlib.util.spec_from_file_location(
    "single_stock_speculation",
    Path(__file__).resolve().parents[1] / "analysis/single_stock_speculation.py",
)
sss = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sss)


def test_predict_and_evaluate(tmp_path):
    # Используем временный файл для прогнозов
    sss.PREDICTIONS_FILE = tmp_path / "predictions.json"

    df = pd.DataFrame(
        {
            "TRADEDATE": pd.date_range("2024-01-01", periods=5),
            "CLOSE": [100, 101, 102, 103, 110],
        }
    )

    with patch.object(sss, "MOEXService") as MockService:
        mock_service = MockService.return_value
        mock_service.get_ticker_data.return_value = df
        with patch.object(sss, "datetime") as mock_dt:
            mock_dt.now.return_value = datetime(
                2024, 1, 10, 11, 0, tzinfo=ZoneInfo("Europe/Moscow")
            )
            record = sss.predict_stock_direction("SBER")
    assert record["prediction"] == "down"
    assert sss.PREDICTIONS_FILE.exists()

    eval_df = pd.DataFrame(
        {"TRADEDATE": [pd.Timestamp("2024-01-10")], "CLOSE": [108]}
    )
    with patch.object(sss, "MOEXService") as MockService:
        mock_service = MockService.return_value
        mock_service.get_ticker_data.return_value = eval_df
        with patch.object(sss, "datetime") as mock_dt:
            mock_dt.now.return_value = datetime(
                2024, 1, 10, 19, 10, tzinfo=ZoneInfo("Europe/Moscow")
            )
            result = sss.evaluate_prediction("SBER")
    assert result["was_correct"] is True
