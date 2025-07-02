import pytest
from models import Portfolio, PortfolioPosition
from utils import calculate_portfolio_value


def test_calculate_portfolio_value():
    portfolio = Portfolio(positions=[
        PortfolioPosition(ticker="AAA", quantity=2),
        PortfolioPosition(ticker="BBB", quantity=3),
    ])

    prices = {"AAA": 10.0, "BBB": 20.0}
    total = calculate_portfolio_value(portfolio, lambda t: prices[t])
    assert total == 2 * 10.0 + 3 * 20.0


def test_calculate_portfolio_value_error(caplog):
    portfolio = Portfolio(positions=[PortfolioPosition(ticker="AAA", quantity=1)])

    def raise_error(ticker: str):
        raise Exception("no price")

    with caplog.at_level("ERROR"):
        total = calculate_portfolio_value(portfolio, raise_error)

    assert total == 0.0
    assert any("Price for AAA" in msg for msg in caplog.text.splitlines())
