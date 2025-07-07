import pytest
from pydantic import ValidationError
from models.state import Portfolio, PortfolioPosition, AnalysisResult


class TestPortfolioPosition:
    """Тесты для модели PortfolioPosition"""
    
    def test_valid_position(self):
        """Тест создания валидной позиции"""
        position = PortfolioPosition(ticker="SBER", quantity=100)
        assert position.ticker == "SBER"
        assert position.quantity == 100
    
    def test_ticker_uppercase(self):
        """Тест автоматического перевода тикера в верхний регистр"""
        position = PortfolioPosition(ticker="sber", quantity=100)
        assert position.ticker == "SBER"
    
    def test_invalid_ticker_too_short(self):
        """Тест валидации слишком короткого тикера"""
        with pytest.raises(ValidationError) as exc_info:
            PortfolioPosition(ticker="AB", quantity=100)
        assert "at least 3 characters" in str(exc_info.value)
    
    def test_invalid_ticker_empty(self):
        """Тест валидации пустого тикера"""
        with pytest.raises(ValidationError) as exc_info:
            PortfolioPosition(ticker="", quantity=100)
        assert "at least 3 characters" in str(exc_info.value)
    
    def test_zero_quantity_allowed(self):
        """Нулевое количество теперь допустимо"""
        position = PortfolioPosition(ticker="SBER", quantity=0)
        assert position.quantity == 0
    
    def test_invalid_quantity_negative(self):
        """Тест валидации отрицательного количества"""
        with pytest.raises(ValidationError) as exc_info:
            PortfolioPosition(ticker="SBER", quantity=-10)
        assert "non-negative" in str(exc_info.value)


class TestPortfolio:
    """Тесты для модели Portfolio"""
    
    def test_valid_portfolio(self):
        """Тест создания валидного портфеля"""
        positions = [
            PortfolioPosition(ticker="SBER", quantity=100),
            PortfolioPosition(ticker="GAZP", quantity=50)
        ]
        portfolio = Portfolio(positions=positions)
        assert len(portfolio.positions) == 2
        assert portfolio.positions[0].ticker == "SBER"
    
    def test_from_dict(self):
        """Тест создания портфеля из словаря"""
        data = {"SBER": 100, "GAZP": 50}
        portfolio = Portfolio.from_dict(data)
        assert len(portfolio.positions) == 2
        tickers = [pos.ticker for pos in portfolio.positions]
        assert "SBER" in tickers
        assert "GAZP" in tickers

    def test_from_dict_with_cash(self):
        """Тест создания портфеля с наличными"""
        data = {"SBER": 100, "RUB": 1000}
        portfolio = Portfolio.from_dict(data)
        assert len(portfolio.positions) == 1
        assert portfolio.cash_rub == 1000
    
    def test_from_dict_empty(self):
        """Тест создания пустого портфеля"""
        portfolio = Portfolio.from_dict({})
        assert len(portfolio.positions) == 0
    
    def test_get_tickers(self):
        """Тест получения списка тикеров"""
        data = {"SBER": 100, "GAZP": 50}
        portfolio = Portfolio.from_dict(data)
        tickers = portfolio.get_tickers()
        assert set(tickers) == {"SBER", "GAZP"}
    
    def test_get_position(self):
        """Тест получения позиции по тикеру"""
        data = {"SBER": 100, "GAZP": 50}
        portfolio = Portfolio.from_dict(data)
        position = portfolio.get_position("SBER")
        assert position is not None
        assert position.quantity == 100
        
        # Тест несуществующей позиции
        position = portfolio.get_position("UNKNOWN")
        assert position is None


class TestAnalysisResult:
    """Тесты для модели AnalysisResult"""
    
    def test_valid_analysis_result(self):
        """Тест создания валидного результата анализа"""
        result = AnalysisResult(
            ticker="SBER",
            recommendation="КУПИТЬ",
            confidence=0.8,
            analysis_data={"test": "data"}
        )
        assert result.ticker == "SBER"
        assert result.recommendation == "КУПИТЬ"
        assert result.confidence == 0.8
        assert result.analysis_data == {"test": "data"}
    
    def test_confidence_validation(self):
        """Тест валидации уверенности"""
        # Валидные значения
        result = AnalysisResult(
            ticker="SBER", recommendation="КУПИТЬ", 
            confidence=0.0, analysis_data={}
        )
        assert result.confidence == 0.0
        
        result = AnalysisResult(
            ticker="SBER", recommendation="КУПИТЬ", 
            confidence=1.0, analysis_data={}
        )
        assert result.confidence == 1.0
        
        # Невалидные значения
        with pytest.raises(ValidationError):
            AnalysisResult(
                ticker="SBER", recommendation="КУПИТЬ", 
                confidence=-0.1, analysis_data={}
            )
        
        with pytest.raises(ValidationError):
            AnalysisResult(
                ticker="SBER", recommendation="КУПИТЬ", 
                confidence=1.1, analysis_data={}
            )