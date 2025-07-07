import pytest
from analyzers import RebalancingAnalyzer
from models import Portfolio, PortfolioPosition, AnalysisResult


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

    price_data = {"AAA": 100.0, "BBB": 10.0}
    analyzer = RebalancingAnalyzer(price_getter=lambda t: price_data[t])
    result = analyzer.suggest_rebalancing(analysis_results, portfolio)

    assert result["AAA"].startswith("Продать")
    assert result["BBB"].startswith("Купить")
    assert result["RUB"].startswith("Остаток")
