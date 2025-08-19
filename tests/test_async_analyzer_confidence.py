import pytest
from analyzers import AsyncPortfolioAnalyzer
from models import Portfolio, PortfolioPosition


@pytest.mark.asyncio
async def test_async_confidence_from_agents(monkeypatch):
    analyzer = AsyncPortfolioAnalyzer()

    def fake_generate_market_news(self, state):
        return {"market_news": ""}

    def fake_generate_news(self, state):
        return {"news": []}

    def fake_grade_news(self, state):
        return {"semantic": ""}

    def fake_moex_news(self, state):
        return {"moex_data": ""}

    def fake_make_trade_analysis(self, state):
        return {"moex_data_analysis": ""}

    def fake_ifrs_analysis(self, state):
        return {"ifrs_data": ""}

    def fake_final_analysis(self, state):
        return {
            "final_data": "Рекомендация: КУПИТЬ",
            "agent_votes": {"A": "КУПИТЬ", "B": "КУПИТЬ"},
            "agent_confidences": {"A": 0.6, "B": 0.8},
        }

    monkeypatch.setattr(AsyncPortfolioAnalyzer, "generate_market_news", fake_generate_market_news)
    monkeypatch.setattr(AsyncPortfolioAnalyzer, "generate_news", fake_generate_news)
    monkeypatch.setattr(AsyncPortfolioAnalyzer, "grade_news", fake_grade_news)
    monkeypatch.setattr(AsyncPortfolioAnalyzer, "moex_news", fake_moex_news)
    monkeypatch.setattr(AsyncPortfolioAnalyzer, "make_trade_analysis", fake_make_trade_analysis)
    monkeypatch.setattr(AsyncPortfolioAnalyzer, "ifrs_analysis", fake_ifrs_analysis)
    monkeypatch.setattr(AsyncPortfolioAnalyzer, "final_analysis", fake_final_analysis)
    monkeypatch.setattr(analyzer.moex_service, "get_returns", lambda ticker: [0.1])

    portfolio = Portfolio(positions=[PortfolioPosition(ticker="AAA", quantity=1)])
    results = await analyzer.analyze_portfolio_async(portfolio)
    assert results["AAA"].confidence == pytest.approx(0.7)
