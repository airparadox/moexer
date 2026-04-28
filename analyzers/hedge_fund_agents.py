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
# Включаем сбор данных для observe-декоратора
os.environ["LANGFUSE_ENABLE"] = "true"


from langfuse import observe
from langfuse import Langfuse


langfuse = None
if os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY"):
    langfuse = Langfuse(
        host="http://localhost:3000",
        public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
        secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
    )

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
        trace = None

        if langfuse:
            trace = langfuse.trace(
                name="hedge-fund-agents",
                input={
                    "ticker": ticker,
                    "summary": summary,
                    "agents": [agent.name for agent in self.agents],
                },
            )

        try:
            for agent in self.agents:
                agent_span = trace.span(name=f"agent-{agent.name}") if trace else None
                try:
                    system_prompt = f"""Ты выступаешь в роли {agent.name} — {agent.description}.

ТВОЯ ЗАДАЧА:
Проанализировать предоставленные данные о компании и сформулировать инвестиционную рекомендацию, 
руководствуясь исключительно своей инвестиционной философией и предоставленными данными.

МЕТОДОЛОГИЯ АНАЛИЗА (выполни пошагово):
1. Примени свою инвестиционную философию к предоставленным данным
2. Выяви ключевые факторы, соответствующие твоему стилю инвестирования
3. Оцени риски и возможности через призму своего подхода
4. Сформулируй рекомендацию с указанием уровня уверенности

ФОРМАТ ОТВЕТА (строго следуй структуре):
=== РЕКОМЕНДАЦИЯ ===
[ОДНО СЛОВО БОЛЬШИМИ БУКВАМИ: КУПИТЬ / ДЕРЖАТЬ / ПРОДАВАТЬ]

=== УВЕРЕННОСТЬ ===
[X]/100 — [краткое обоснование уровня уверенности]

=== ДОВОДЫ (максимум 3) ===
• [Довод 1]: [кратко, строго из данных]
• [Довод 2]: [кратко, строго из данных]
• [Довод 3]: [кратко, строго из данных]

=== КРАСНЫЕ ФЛАГИ (максимум 2) ===
• [Флаг 1]: [краткое описание риска]
• [Флаг 2]: [краткое описание риска]

=== ГОРИЗОНТ ===
[Рекомендуемый инвестиционный горизонт, например: 3-6 месяцев, 1-2 года]

ПРАВИЛА:
1. Учитывай веса источников данных: IFRS, NEWS, MOEX, SOCIAL
2. При конфликте данных приоритизируй источники с большим весом
3. При равных весах и противоречивых сигналах — склоняйся к ДЕРЖАТЬ
4. НЕ ссылайся на свою репутацию или прошлые кейсы
5. Решение принимай ТОЛЬКО по предоставленным данным
6. Не выдумывай фактов. Если данных недостаточно — явно укажи это и снизь уверенность
7. Будь конкретен, избегай общих фраз

ВАЖНО: Твоя рекомендация должна отражать уникальную перспективу {agent.name}, 
но основываться ИСКЛЮЧИТЕЛЬНО на предоставленных фактических данных."""

                    user_prompt = f"Анализ по {ticker}:\n{summary}"
                    response = self.ai_service.call_model(system_prompt, user_prompt)
                    votes[agent.name] = extract_recommendation(response)
                    confidences[agent.name] = extract_confidence(response)

                    if agent_span:
                        agent_span.end(
                            output={
                                "recommendation": votes[agent.name],
                                "confidence": confidences[agent.name],
                            }
                        )
                except APIError as e:
                    logger.error(f"Agent {agent.name} API error: {e}")
                    votes[agent.name] = "ДЕРЖАТЬ"
                    confidences[agent.name] = 0.0
                    if agent_span:
                        agent_span.end(output={"error": str(e)})
                except Exception as e:
                    logger.error(f"Agent {agent.name} failed: {e}")
                    votes[agent.name] = "ДЕРЖАТЬ"
                    confidences[agent.name] = 0.0
                    if agent_span:
                        agent_span.end(output={"error": str(e)})

            if trace:
                trace.update(output={"votes": votes, "confidences": confidences})
        finally:
            if langfuse:
                langfuse.flush()

        return votes, confidences
