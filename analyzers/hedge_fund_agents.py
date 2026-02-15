import logging
from dataclasses import dataclass
from typing import Dict, List
import os

from services.ai_service import AIService
from utils.helpers import APIError, extract_recommendation, extract_confidence

logger = logging.getLogger(__name__)

# ❗ Жёстко указываем OTEL endpoint на локальный Langfuse
os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = "http://localhost:3000/api/public/otel"
os.environ["OTEL_EXPORTER_OTLP_PROTOCOL"] = "http/protobuf"

# Можно дополнительно отключить retries
os.environ["OTEL_EXPORTER_OTLP_TRACES_ENDPOINT"] = "http://localhost:3000/api/public/otel/v1/traces"

# (по желанию) чтобы точно не было cloud fallback
os.environ["LANGFUSE_HOST"] = "http://localhost:3000"


from langfuse import observe
from langfuse import Langfuse

@dataclass
class InvestorAgent:
    """Описание инвестора-агента"""
    name: str
    description: str

class HedgeFundAgents:
    """Простая реализация мультиагентного анализа, вдохновлённая проектом AI Hedge Fund."""
    @observe()
    def __init__(self, ai_service: AIService):
        self.ai_service = ai_service
        self.agents: List[InvestorAgent] = [
            InvestorAgent(
                "Warren Buffett",
                (
                    "легендарный стоимостной инвестор, ищущий недооценённые компании\n"
                    "Дополнительные критерии:\n"
                    "- Маржа безопасности: дисконт к справедливой/исторической оценке.\n"
                    "- Экономические рвы: устойчивые конкурентные преимущества.\n"
                    "- Финансовая устойчивость: долговая нагрузка, качество прибыли, FCF.\n"
                    "Если оценка кажется завышенной или устойчивость сомнительна — склоняйся к ДЕРЖАТЬ/ПРОДАВАТЬ."
                ),
            ),
            InvestorAgent(
                "Cathie Wood",
                (
                    "ориентирована на рост и инновации\n"
                    "Дополнительные критерии:\n"
                    "- Дисраптивность и TAM: потенциал экспоненциального роста выручки.\n"
                    "- Технологические/регуляторные катализаторы.\n"
                    "- Долгосрочная траектория, допускающая краткосрочную волатильность.\n"
                    "Если краткосрочная слабость, но сильные катализаторы и большой TAM — допускай КУПИТЬ с оговорками."
                ),
            ),
            InvestorAgent(
                "Peter Lynch",
                (
                    "практичный инвестор, охотящийся за 'ten-baggers'\n"
                    "Дополнительные критерии:\n"
                    "- Простая «история роста»: что именно разгонит прибыль.\n"
                    "- PEG/оценка vs рост (если можно оценить по данным).\n"
                    "- «Знаешь, что владеешь»: избегай туманности.\n"
                    "Если история неясна — ДЕРЖАТЬ."
                ),
            ),
        ]
    @observe()
    def analyze(self, ticker: str, summary: str) -> tuple[Dict[str, str], Dict[str, float]]:
        """Возвращает рекомендации и уверенности каждого агента."""
        votes: Dict[str, str] = {}
        confidences: Dict[str, float] = {}
        for agent in self.agents:
            try:
                system_prompt = (
                    f"Ты выступаешь как {agent.name} — {agent.description}."
                    f"Но ты НЕ можешь ссылаться на свою репутацию или прошлые кейсы; решение принимается ТОЛЬКО по предоставленным данным и весам источников."
                    f"В начале ответа выведи РОВНО ОДНО слово (большими буквами):"
                    f"КУПИТЬ / ДЕРЖАТЬ / ПРОДАВАТЬ"
                    f"Далее выдай:"
                    f"Уверенность: X/100"
                    f"Доводы (до 3 пунктов):"
                    f"- [TAG] кратко по сути, строго из данных"
                    f"Красные флаги (до 2):"
                    f"- [TAG] кратко"
                    f"Горизонт: кратко (например, 3–6 мес)"
                    f"Общие правила:"
                    f"1) Учитывай веса источников: [IFRS, NEWS, MOEX, SOCIAL]."
                    f"2) При конфликте данных приоритизируй по весам. При равенстве — ДЕРЖАТЬ."
                    f"3) Не выдумывай фактов. Если чего-то не хватает — понижай уверенность."
                )

                user_prompt = f"Анализ по {ticker}:\n{summary}"
                response = self.ai_service.call_model(system_prompt, user_prompt)
                votes[agent.name] = extract_recommendation(response)
                confidences[agent.name] = extract_confidence(response)
            except APIError as e:
                logger.error(f"Agent {agent.name} API error: {e}")
                votes[agent.name] = "ДЕРЖАТЬ"
                confidences[agent.name] = 0.0
            except Exception as e:
                logger.error(f"Agent {agent.name} failed: {e}")
                votes[agent.name] = "ДЕРЖАТЬ"
                confidences[agent.name] = 0.0
        return votes, confidences
