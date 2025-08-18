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
                f"Warren Buffett"
                f"легендарный стоимостной инвестор, ищущий недооценённые компании"
                f"Дополнительные критерии:"
                f"- Маржа безопасности: дисконт к справедливой/исторической оценке."
                f"- Экономические рвы: устойчивые конкурентные преимущества."
                f"- Финансовая устойчивость: долговая нагрузка, качество прибыли, FCF."
                f"Если оценка кажется завышенной или устойчивость сомнительна — склоняйся к ДЕРЖАТЬ/ПРОДАВАТЬ."

        ),
            InvestorAgent(
                f"Cathie Wood",
                f"ориентирована на рост и инновации"
                f"Дополнительные критерии:"
                f"- Дисраптивность и TAM: потенциал экспоненциального роста выручки."
                f"- Технологические/регуляторные катализаторы."
                f"- Долгосрочная траектория, допускающая краткосрочную волатильность."

                f"Если краткосрочная слабость, но сильные катализаторы и большой TAM — допускай КУПИТЬ с оговорками."

        ),
            InvestorAgent(
                "Peter Lynch",
                f"практичный инвестор, охотящийся за 'ten-baggers'"
                f"Дополнительные критерии:"
                f"- Простая «история роста»: что именно разгонит прибыль."
                f"- PEG/оценка vs рост (если можно оценить по данным)."
                f"- «Знаешь, что владеешь»: избегай туманности."

                f"Если история неясна — ДЕРЖАТЬ."

        ),
        ]

    def analyze(self, ticker: str, summary: str) -> Dict[str, str]:
        """Возвращает рекомендации каждого агента."""
        votes: Dict[str, str] = {}
        for agent in self.agents:
            try:
                # system_prompt = (
                #     f"Ты {agent.name}, {agent.description}. "
                #     "Ответь в формате: КУПИТЬ/ДЕРЖАТЬ/ПРОДАТЬ и короткое обоснование."
                # )

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
            except Exception as e:
                logger.error(f"Agent {agent.name} failed: {e}")
                votes[agent.name] = "ДЕРЖАТЬ"
        return votes
