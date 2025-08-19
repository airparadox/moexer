import logging
import os
from typing import Dict, Optional
from langsmith import traceable
from langgraph.graph import StateGraph, START, END
from io import StringIO
import pandas as pd

from models.state import State, Portfolio, AnalysisResult, RiskProfile
from services.ai_service import AIService
from services.news_service import NewsService
from services.moex_service import MOEXService
from services.ifrs_service import IFRSService
from utils.helpers import (
    APIError,
    DataProcessingError,
    truncate_text,
    extract_recommendation,
)
from utils.pmpt import pmpt_metrics

logger = logging.getLogger(__name__)

# Веса источников данных для финального анализа
WEIGHTS = {
    "ifrs": 0.55,            # МСФО-отчётность, фундаментал
    "market_news": 0.20,     # Новости от информагентств
    "moex": 0.15,            # Биржевые данные (объёмы, ликвидность)
    "social": 0.10,          # Соцсети
}

class PortfolioAnalyzer:
    """Основной класс для анализа портфеля"""

    def __init__(self, api_key: Optional[str] = None):
        key = api_key or os.getenv("DEEPSEEK_API_KEY", "dummy")
        self.ai_service = AIService(api_key=key)
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
                
                analysis = self.ai_service.call_model(system_prompt, user_prompt)
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
            user_prompt = f"Новости {state['ticker']}:\n{state['news']}"
            
            analysis = self.ai_service.call_model(system_prompt, user_prompt)
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
            
            # Используем сервис для получения последних 180 дней
            recent_data = self.moex_service.get_recent_data(state['ticker'], 180)
            user_prompt = f"Данные {state['ticker']}:\n{recent_data}"
            
            analysis = self.ai_service.call_model(system_prompt, user_prompt)
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
            
            analysis = self.ai_service.call_model(system_prompt, user_prompt)
            return {"ifrs_data": analysis}
            
        except (APIError, DataProcessingError, Exception) as e:
            logger.error(f"IFRS error {state['ticker']}: {e}")
            return {"ifrs_data": "Ошибка анализа МСФО"}

    @traceable

    def final_analysis(self, state: State) -> dict:
        """Финальный анализ и рекомендация"""
        try:
            # 1) Сначала всё, что нужно для форматирования
            risk = state.get('risk_profile', RiskProfile.BALANCED.value)
            goal_map = {
                RiskProfile.CONSERVATIVE.value: "Цель: стабильный доход и минимум риска",
                RiskProfile.BALANCED.value: "Цель: умеренный рост с контролем риска",
                RiskProfile.AGGRESSIVE.value: "Цель: максимальный рост, готовность к риску",
                RiskProfile.SPECULATIVE.value: "Цель: активные спекуляции и частая ребалансировка",
            }

            # 2) Ограничиваем длину блоков данных
            market_news = truncate_text(state.get('market_news', ''), 3000)
            semantic = truncate_text(state.get('semantic', ''), 3000)
            moex_analysis = truncate_text(state.get('moex_data_analysis', ''), 3000)
            ifrs_data = truncate_text(state.get('ifrs_data', ''), 3000)

            # 3) Формируем подсказки
            system_prompt = (
                "Ты — инвестиционный директор хедж-фонда."
                " Твоя задача: на основе данных о компании и рыночной ситуации подготовить финальную рекомендацию в формате:\n"
                "- КУПИТЬ / ДЕРЖАТЬ / ПРОДАВАТЬ (выбери строго одно действие)\n"
                "- Краткое объяснение на 2–3 предложения для управляющего портфелем\n\n"
                "Правила:\n"
                "1. Всегда учитывай весовые коэффициенты источников данных:\n"
                f"- МСФО и фундаментал — {WEIGHTS['ifrs']*100:.0f}%\n"
                f"- Новости агентств — {WEIGHTS['market_news']*100:.0f}%\n"
                f"- Биржевые данные — {WEIGHTS['moex']*100:.0f}%\n"
                f"- Соцсети — {WEIGHTS['social']*100:.0f}%\n"
                "2. Если позиция ещё не открыта → рекомендация: КУПИТЬ / ДЕРЖАТЬ / ПРОДАВАТЬ (где ДЕРЖАТЬ означает «воздержаться от покупки»).\n"
                "3. Если позиция уже есть → рекомендация: УВЕЛИЧИТЬ / СОКРАТИТЬ / ДЕРЖАТЬ.\n"
                f"4. Учитывай профиль инвестора: {risk}. {goal_map.get(risk, '')}\n"
                "5. Форматируй ответ чётко, без воды.\n\n"
                "Стиль ответа: как на заседании инвестиционного комитета хедж-фонда."
            )

            user_prompt = (
                f"Сводка по {state['ticker']}:\n"
                f"- Финансы (вес {WEIGHTS['ifrs']*100:.0f}%): {ifrs_data}\n"
                f"- Новости от информагентств (вес {WEIGHTS['market_news']*100:.0f}%): {market_news}\n"
                f"- Биржевые данные (вес {WEIGHTS['moex']*100:.0f}%): {moex_analysis}\n"
                f"- Соцсети (вес {WEIGHTS['social']*100:.0f}%): {semantic}\n"
                f"Тип инвестора: {risk}. {goal_map.get(risk, '')}"
            )

            analysis = self.ai_service.call_model(system_prompt, user_prompt) or "Нет ответа модели"

            # Мультиагентный анализ (не обязательно критичен)
            try:
                from .hedge_fund_agents import HedgeFundAgents
                summary = (
                    f"Рынок: {market_news}\n"
                    f"Компания: {semantic}\n"
                    f"График: {moex_analysis}\n"
                    f"Финансы: {ifrs_data}"
                )
                agents = HedgeFundAgents(self.ai_service)
                votes, confidences = agents.analyze(state["ticker"], summary)
            except Exception as e:
                logger.error(f"Hedge fund agents failed {state['ticker']}: {e}")
                votes, confidences = {}, {}

            return {
                "final_data": analysis,
                "agent_votes": votes,
                "agent_confidences": confidences,
            }

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
                "final_data": "",
                "risk_profile": portfolio.risk_profile.value
            }

            logger.info(f"Processing {position.ticker} with quantity {position.quantity}")
            
            try:
                result = chain.invoke(initial_state)
                
                # Извлекаем рекомендацию из финального анализа более надёжным способом
                votes = result.get("agent_votes", {})
                confidences = result.get("agent_confidences", {})
                if votes:
                    decisions = list(votes.values())
                    recommendation = max(set(decisions), key=decisions.count)
                else:
                    recommendation = extract_recommendation(result["final_data"])

                if confidences:
                    confidence = sum(confidences.values()) / len(confidences)
                else:
                    confidence = 0.0

                analysis_result = AnalysisResult(
                    ticker=position.ticker,
                    recommendation=recommendation,
                    confidence=confidence,
                    analysis_data={
                        "market_news": result["market_news"],
                        "semantic": result["semantic"],
                        "moex_analysis": result["moex_data_analysis"],
                        "ifrs_data": result["ifrs_data"],
                        "final_decision": result["final_data"],
                        "agent_votes": votes,
                        "agent_confidences": confidences,
                    }
                )

                try:
                    returns = self.moex_service.get_returns(position.ticker)
                    analysis_result.analysis_data["pmpt"] = pmpt_metrics(returns)
                except Exception as e:
                    logger.error(f"Failed to compute PMPT for {position.ticker}: {e}")
                    analysis_result.analysis_data["pmpt"] = {}
                
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
