import pandas as pd
import apimoex
import pytest

from services import MOEXService


def test_get_ticker_data_marks_dividend_days(monkeypatch):
    service = MOEXService()

    sample = [
        {"TRADEDATE": "2025-01-07", "CLOSE": 100, "VOLUME": 10, "VALUE": 1000},
        {"TRADEDATE": "2025-01-09", "CLOSE": 95, "VOLUME": 12, "VALUE": 1140},
    ]

    def fake_get_board_history(session, ticker, start, end):
        return sample

    monkeypatch.setattr(apimoex, "get_board_history", fake_get_board_history)

    df = service.get_ticker_data("TATN", days_back=5)

    assert df.loc[df["TRADEDATE"] == pd.Timestamp("2025-01-07"), "IS_DIVIDEND_DAY"].iloc[0]
    assert not df.loc[df["TRADEDATE"] == pd.Timestamp("2025-01-09"), "IS_DIVIDEND_DAY"].iloc[0]

