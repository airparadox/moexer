from datetime import datetime

import pandas as pd

from models import RecommendationRecord
from services.db_service import RecommendationDB
from services.backtest_service import BacktestService


def test_backtest_simple(tmp_path, mocker):
    db_path = tmp_path / "rec.db"
    db = RecommendationDB(db_path)
    rec = RecommendationRecord(
        ticker="SBER",
        recommendation="КУПИТЬ",
        confidence=0.8,
        price=100.0,
        timestamp=datetime(2024, 1, 1),
    )
    db.save(rec)
    db.close()

    df = pd.DataFrame(
        {
            "TRADEDATE": [pd.Timestamp("2024-01-01"), pd.Timestamp("2024-01-06")],
            "CLOSE": [100.0, 110.0],
            "VOLUME": [0, 0],
            "VALUE": [0, 0],
        }
    )
    mocker.patch(
        "services.backtest_service.MOEXService.get_ticker_data", return_value=df
    )

    service = BacktestService(db_path)
    stats = service.run_backtest(holding_period=5)
    assert stats["total"] == 1
    assert stats["correct"] == 1
    assert abs(stats["avg_return"] - 0.1) < 1e-6
