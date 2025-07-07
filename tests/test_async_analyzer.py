import asyncio
import pytest
from analyzers import AsyncPortfolioAnalyzer
from models import Portfolio, PortfolioPosition, AnalysisResult


@pytest.mark.asyncio
async def test_analyze_portfolio_async(monkeypatch):
    analyzer = AsyncPortfolioAnalyzer(max_concurrent_tasks=2)

    async def fake_analyze_single(chain, position, risk_profile):
        await asyncio.sleep(0.01)
        return position.ticker, AnalysisResult(
            ticker=position.ticker,
            recommendation="КУПИТЬ",
            confidence=1.0,
            analysis_data={},
        )

    monkeypatch.setattr(analyzer, "_analyze_single", fake_analyze_single)

    portfolio = Portfolio(positions=[
        PortfolioPosition(ticker="AAA", quantity=1),
        PortfolioPosition(ticker="BBB", quantity=2),
    ])

    result = await analyzer.analyze_portfolio_async(portfolio)

    assert set(result.keys()) == {"AAA", "BBB"}
    assert all(r.recommendation == "КУПИТЬ" for r in result.values())
