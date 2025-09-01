import time

import importlib.util
import sys
import types
import time
from pathlib import Path

import pandas as pd
import pytest

from models import AnalysisResult, Portfolio

services_module = types.ModuleType("services")
spec_moex = importlib.util.spec_from_file_location(
    "moex_service", Path(__file__).resolve().parents[1] / "services" / "moex_service.py"
)
moex_module = importlib.util.module_from_spec(spec_moex)
spec_moex.loader.exec_module(moex_module)  # type: ignore[arg-type]
services_module.moex_service = moex_module
sys.modules["services"] = services_module
sys.modules["services.moex_service"] = moex_module

spec = importlib.util.spec_from_file_location(
    "rebalancing_analyzer", Path(__file__).resolve().parents[1] / "analyzers" / "rebalancing_analyzer.py"
)
rebalancing_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rebalancing_module)  # type: ignore[arg-type]
RebalancingAnalyzer = rebalancing_module.RebalancingAnalyzer


def test_suggest_rebalancing_with_cash():
    portfolio = Portfolio.from_dict({"AAA": 10, "BBB": 5, "RUB": 1000})
    analysis_results = {
        "AAA": AnalysisResult(
            ticker="AAA", recommendation="ПРОДАВАТЬ", confidence=1.0, analysis_data={}
        ),
        "BBB": AnalysisResult(
            ticker="BBB", recommendation="КУПИТЬ", confidence=1.0, analysis_data={}
        ),
    }

    price_df = pd.DataFrame({"price": [100.0, 10.0]}, index=["AAA", "BBB"])
    analyzer = RebalancingAnalyzer(price_getter=lambda ts: price_df.loc[ts])
    result = analyzer.suggest_rebalancing(analysis_results, portfolio)

    assert result["AAA"].startswith("Продать")
    assert result["BBB"].startswith("Купить")
    assert result["RUB"].startswith("Остаток")


def test_rebalancing_zero_quantity_sell():
    """Продажа невозможна при нулевой позиции."""
    portfolio = Portfolio.from_dict({"AAA": 0, "RUB": 1000})
    analysis_results = {
        "AAA": AnalysisResult(
            ticker="AAA", recommendation="ПРОДАВАТЬ", confidence=1.0, analysis_data={}
        ),
    }

    price_df = pd.DataFrame({"price": [100.0]}, index=["AAA"])
    analyzer = RebalancingAnalyzer(price_getter=lambda ts: price_df.loc[ts])
    result = analyzer.suggest_rebalancing(analysis_results, portfolio)

    assert "AAA" not in result


def test_rebalancing_considers_confidence():
    portfolio = Portfolio.from_dict({"AAA": 0, "BBB": 0, "RUB": 10000})
    analysis_results = {
        "AAA": AnalysisResult(
            ticker="AAA", recommendation="КУПИТЬ", confidence=1.0, analysis_data={}
        ),
        "BBB": AnalysisResult(
            ticker="BBB", recommendation="КУПИТЬ", confidence=0.5, analysis_data={}
        ),
    }

    price_df = pd.DataFrame({"price": [1000.0, 1000.0]}, index=["AAA", "BBB"])
    analyzer = RebalancingAnalyzer(price_getter=lambda ts: price_df.loc[ts])
    result = analyzer.suggest_rebalancing(analysis_results, portfolio)

    assert result["AAA"] == "Купить 6"
    assert result["BBB"] == "Купить 3"


def test_rebalancing_many_assets_performance():
    tickers = [f"T{i:03d}" for i in range(200)]
    portfolio_data = {t: 0 for t in tickers}
    portfolio_data["RUB"] = 100000
    portfolio = Portfolio.from_dict(portfolio_data)

    analysis_results = {
        t: AnalysisResult(ticker=t, recommendation="КУПИТЬ", confidence=1.0, analysis_data={})
        for t in tickers
    }

    prices = pd.DataFrame({"price": [10 + i for i in range(200)]}, index=tickers)
    analyzer = RebalancingAnalyzer(price_getter=lambda ts: prices.loc[ts])

    start = time.time()
    suggestions = analyzer.suggest_rebalancing(analysis_results, portfolio)
    duration = time.time() - start

    assert duration < 1.0
    assert len([t for t in suggestions if t != "RUB"]) <= len(tickers)

