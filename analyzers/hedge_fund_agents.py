import logging
from dataclasses import dataclass
from typing import Dict, List

from services.ai_service import AIService
from utils.helpers import extract_recommendation

logger = logging.getLogger(__name__)

@dataclass
class InvestorAgent:
    """Описание инвестора-агента"""
    name: str
    description: str

class HedgeFundAgents:
    """Простая реализация мультиагентного анализа, вдохновлённая проектом AI Hedge Fund."""

    def __init__(self, ai_service: AIService):
        self.ai_service = ai_service
        self.agents: List[InvestorAgent] = [
            InvestorAgent(
                "Warren Buffett",
                "легендарный стоимостной инвестор, ищущий недооценённые компании",
            ),
            InvestorAgent(
                "Cathie Wood",
                "ориентирована на рост и инновации",
            ),
            InvestorAgent(
                "Peter Lynch",
                "практичный инвестор, охотящийся за 'ten-baggers'",
            ),
        ]

    def analyze(self, ticker: str, summary: str) -> Dict[str, str]:
        """Возвращает рекомендации каждого агента."""
        votes: Dict[str, str] = {}
        for agent in self.agents:
            try:
                system_prompt = (
                    f"Ты {agent.name}, {agent.description}. "
                    "Ответь в формате: КУПИТЬ/ДЕРЖАТЬ/ПРОДАТЬ и короткое обоснование."
                )
                user_prompt = f"Анализ по {ticker}:\n{summary}"
                response = self.ai_service.call_deepseek(system_prompt, user_prompt)
                votes[agent.name] = extract_recommendation(response)
            except Exception as e:
                logger.error(f"Agent {agent.name} failed: {e}")
                votes[agent.name] = "ДЕРЖАТЬ"
        return votes
