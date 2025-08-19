import pytest
from analyzers import PortfolioAnalyzer, RebalancingAnalyzer
from models import Portfolio


def test_final_decision_aligns_with_rebalancing(monkeypatch):
    analyzer = PortfolioAnalyzer()

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
            "agent_votes": {"A": "ДЕРЖАТЬ", "B": "ДЕРЖАТЬ"},
            "agent_confidences": {},
        }

    monkeypatch.setattr(PortfolioAnalyzer, "generate_market_news", fake_generate_market_news)
    monkeypatch.setattr(PortfolioAnalyzer, "generate_news", fake_generate_news)
    monkeypatch.setattr(PortfolioAnalyzer, "grade_news", fake_grade_news)
    monkeypatch.setattr(PortfolioAnalyzer, "moex_news", fake_moex_news)
    monkeypatch.setattr(PortfolioAnalyzer, "make_trade_analysis", fake_make_trade_analysis)
    monkeypatch.setattr(PortfolioAnalyzer, "ifrs_analysis", fake_ifrs_analysis)
    monkeypatch.setattr(PortfolioAnalyzer, "final_analysis", fake_final_analysis)
    monkeypatch.setattr(analyzer.moex_service, "get_returns", lambda ticker: [0.1])

    portfolio = Portfolio.from_dict({"AAA": 0, "RUB": 1000})
    results = analyzer.analyze_portfolio(portfolio)
    assert results["AAA"].recommendation == "КУПИТЬ"

    rebalancer = RebalancingAnalyzer(price_getter=lambda t: 100)
    suggestions = rebalancer.suggest_rebalancing(results, portfolio)
    assert suggestions["AAA"].startswith("Купить")

