import logging
from typing import Dict
from langsmith import traceable
from langgraph.graph import StateGraph, START, END
from io import StringIO
import pandas as pd

from models.state import State, Portfolio, AnalysisResult
from services.ai_service import AIService
from services.news_service import NewsService
from services.moex_service import MOEXService
from services.ifrs_service import IFRSService
from utils.helpers import APIError, DataProcessingError, truncate_text

logger = logging.getLogger(__name__)

class PortfolioAnalyzer:
    """Основной класс для анализа портфеля"""
    
    def __init__(self):
        self.ai_service = AIService()
        self.news_service = NewsService()
        self.moex_service = MOEXService()
        self.ifrs_service = IFRSService()
    
    @traceable
    def generate_market_news(self, state: State) -> dict:
        """Получение и анализ новостей с lenta.ru"""
        try:
            news_entries = self.news_service.get_market_news()
            
            if news_entries:
                system_prompt = "Анализ новостей рынка. Формат: Настрой, Факторы, Влияние"
                user_prompt = f"Новости:\n{news_entries}"
                
                analysis = self.ai_service.call_deepseek(system_prompt, user_prompt)
                return {"market_news": analysis}
            
            return {"market_news": "Недостаточно свежих новостей для анализа"}
            
        except (APIError, Exception) as e:
            logger.error(f"Market news error: {e}")
            return {"market_news": "Ошибка при анализе новостей"}

    @traceable
    def generate_news(self, state: State) -> dict:
        """Получение новостей по тикеру"""
        try:
            texts = self.news_service.get_ticker_news(state['ticker'])
            return {"news": texts}
        except (APIError, Exception) as e:
            logger.error(f"News error {state['ticker']}: {e}")
            return {"news": []}

    @traceable
    def grade_news(self, state: State) -> dict:
        """Анализ новостей компании"""
        try:
            if not state['news']:
                return {"semantic": "Нет новостей для анализа"}
            
            system_prompt = "Анализ новостей компании. Формат: Настрой, Ключевое, Риски"
            user_prompt = f"Новости {state['ticker']}:\n{state['news'][:2]}"
            
            analysis = self.ai_service.call_deepseek(system_prompt, user_prompt)
            return {"semantic": analysis}
            
        except (APIError, Exception) as e:
            logger.error(f"Grade error {state['ticker']}: {e}")
            return {"semantic": "Ошибка анализа новостей"}

    @traceable
    def moex_news(self, state: State) -> dict:
        """Получение данных MOEX"""
        try:
            df = self.moex_service.get_ticker_data(state['ticker'])
            return {"moex_data": df.to_string(index=False)}
        except (APIError, Exception) as e:
            logger.error(f"MOEX error {state['ticker']}: {e}")
            return {"moex_data": "Ошибка получения данных MOEX"}

    @traceable
    def make_trade_analysis(self, state: State) -> dict:
        """Технический анализ торговых данных"""
        try:
            if state['moex_data'] == "Ошибка получения данных MOEX":
                return {"moex_data_analysis": "Невозможно провести технический анализ"}
            
            system_prompt = "Теханализ. Формат: Тренд, Объемы, Волатильность"
            
            # Используем сервис для получения последних 20 дней
            recent_data = self.moex_service.get_recent_data(state['ticker'], 20)
            user_prompt = f"Данные {state['ticker']}:\n{recent_data}"
            
            analysis = self.ai_service.call_deepseek(system_prompt, user_prompt)
            return {"moex_data_analysis": analysis}
            
        except (APIError, Exception) as e:
            logger.error(f"Trade analysis error {state['ticker']}: {e}")
            return {"moex_data_analysis": "Ошибка технического анализа"}

    @traceable
    def ifrs_analysis(self, state: State) -> dict:
        """Анализ IFRS отчетности"""
        try:
            ifrs_content = self.ifrs_service.get_ifrs_data(state['ticker'])
            
            if "не найдена" in ifrs_content:
                return {"ifrs_data": ifrs_content}
            
            system_prompt = "Анализ МСФО. Формат: Финансы, Рентабельность, Долги"
            user_prompt = f"Отчетность {state['ticker']}:\n{ifrs_content}"
            
            analysis = self.ai_service.call_deepseek(system_prompt, user_prompt)
            return {"ifrs_data": analysis}
            
        except (APIError, DataProcessingError, Exception) as e:
            logger.error(f"IFRS error {state['ticker']}: {e}")
            return {"ifrs_data": "Ошибка анализа МСФО"}

    @traceable
    def final_analysis(self, state: State) -> dict:
        """Финальный анализ и рекомендация"""
        try:
            system_prompt = "Рекомендация: КУПИТЬ/ДЕРЖАТЬ/ПРОДАВАТЬ с пояснением"
            
            # Ограничиваем длину каждого блока данных
            market_news = truncate_text(state['market_news'], 300)
            semantic = truncate_text(state['semantic'], 300)
            moex_analysis = truncate_text(state['moex_data_analysis'], 300)
            ifrs_data = truncate_text(state['ifrs_data'], 300)
            
            user_prompt = (
                f"Сводка по {state['ticker']}:\n"
                f"- Рынок: {market_news}\n"
                f"- Компания: {semantic}\n"
                f"- График: {moex_analysis}\n"
                f"- Финансы: {ifrs_data}\n"
                "Цель: доход > депозитов, минимум риска"
            )
            
            analysis = self.ai_service.call_deepseek(system_prompt, user_prompt)
            return {"final_data": analysis}
            
        except (APIError, Exception) as e:
            logger.error(f"Final analysis error {state['ticker']}: {e}")
            return {"final_data": "Ошибка финального анализа"}

    def analyze_portfolio(self, portfolio: Portfolio) -> Dict[str, AnalysisResult]:
        """
        Анализирует портфель и возвращает рекомендации по каждому тикеру.
        
        Args:
            portfolio: Портфель для анализа
            
        Returns:
            Словарь с результатами анализа для каждого тикера
            
        Raises:
            APIError: При ошибках обращения к внешним API
            DataProcessingError: При ошибках обработки данных
        """
        workflow = StateGraph(State)

        # Добавляем узлы в граф
        workflow.add_node("generate_market_news", self.generate_market_news)
        workflow.add_node("generate_news", self.generate_news)
        workflow.add_node("grade_news", self.grade_news)
        workflow.add_node("moex_news", self.moex_news)
        workflow.add_node("make_trade_analysis", self.make_trade_analysis)
        workflow.add_node("ifrs_analysis", self.ifrs_analysis)
        workflow.add_node("final_analysis", self.final_analysis)

        # Определяем последовательность выполнения
        workflow.add_edge(START, "generate_market_news")
        workflow.add_edge("generate_market_news", "generate_news")
        workflow.add_edge("generate_news", "grade_news")
        workflow.add_edge("grade_news", "moex_news")
        workflow.add_edge("moex_news", "make_trade_analysis")
        workflow.add_edge("make_trade_analysis", "ifrs_analysis")
        workflow.add_edge("ifrs_analysis", "final_analysis")
        workflow.add_edge("final_analysis", END)

        chain = workflow.compile()
        portfolio_results = {}

        for position in portfolio.positions:
            initial_state = {
                "ticker": position.ticker,
                "quantity": position.quantity,
                "news": "",
                "semantic": "",
                "moex_data": "",
                "moex_data_analysis": "",
                "ifrs_data": "",
                "market_news": "",
                "final_data": ""
            }

            logger.info(f"Processing {position.ticker} with quantity {position.quantity}")
            
            try:
                result = chain.invoke(initial_state)
                
                # Извлекаем рекомендацию из финального анализа
                recommendation = "ДЕРЖАТЬ"  # по умолчанию
                if "КУПИТЬ" in result["final_data"]:
                    recommendation = "КУПИТЬ"
                elif "ПРОДАВАТЬ" in result["final_data"]:
                    recommendation = "ПРОДАВАТЬ"
                
                analysis_result = AnalysisResult(
                    ticker=position.ticker,
                    recommendation=recommendation,
                    confidence=0.8,  # базовый уровень уверенности
                    analysis_data={
                        "market_news": result["market_news"],
                        "semantic": result["semantic"],
                        "moex_analysis": result["moex_data_analysis"],
                        "ifrs_data": result["ifrs_data"],
                        "final_decision": result["final_data"]
                    }
                )
                
                portfolio_results[position.ticker] = analysis_result
                
            except Exception as e:
                logger.error(f"Failed to analyze {position.ticker}: {e}")
                # Создаем результат с ошибкой
                portfolio_results[position.ticker] = AnalysisResult(
                    ticker=position.ticker,
                    recommendation="ДЕРЖАТЬ",
                    confidence=0.0,
                    analysis_data={"error": str(e)}
                )

        return portfolio_results