import logging
from dataclasses import dataclass
from typing import Dict, Optional, Callable, Any, List

from services.ai_service import AIService
from services.ifrs_service import IFRSService
from services.moex_service import MOEXService
from services.news_service import NewsService

logger = logging.getLogger(__name__)


@dataclass
class Agent:
    """Базовый агент, использующий LLM."""

    name: str
    description: str
    ai_service: AIService

    def _ask(self, system_prompt: str, user_prompt: str) -> str:
        """Безопасный вызов модели."""
        try:
            return self.ai_service.call_model(system_prompt, user_prompt)
        except Exception as e:  # pragma: no cover - простая обертка
            logger.error(f"{self.name} failed: {e}")
            return "Ошибка выполнения"

    def _ask_with_tools(
        self,
        system_prompt: str,
        user_prompt: str,
        tools: List[Dict[str, Any]],
        tool_funcs: Dict[str, Callable],
    ) -> str:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        try:
            return self.ai_service.call_with_tools(messages, tools, tool_funcs)
        except Exception as e:  # pragma: no cover - простая обертка
            logger.error(f"{self.name} failed: {e}")
            return "Ошибка выполнения"


class FundamentalAnalysisAgent(Agent):
    """Агент фундаментального анализа через МСФО."""

    def __init__(self, ai_service: AIService, ifrs_service: Optional[IFRSService] = None):
        super().__init__("Фундаментальный аналитик", "анализирует отчетность МСФО", ai_service)
        self.ifrs_service = ifrs_service or IFRSService()

    def analyze(self, ticker: str) -> str:
        def get_ifrs(ticker: str) -> str:
            return self.ifrs_service.get_ifrs_data(ticker)

        tools = [
            {
                "type": "function",
                "function": {
                    "name": "get_ifrs",
                    "description": "Получить данные МСФО по тикеру",
                    "parameters": {
                        "type": "object",
                        "properties": {"ticker": {"type": "string"}},
                        "required": ["ticker"],
                    },
                },
            }
        ]
        system = (
            "Ты финансовый аналитик. Используй get_ifrs для получения отчетности "
            "и дай краткое резюме."
        )
        user = f"Проанализируй компанию {ticker}."
        return self._ask_with_tools(system, user, tools, {"get_ifrs": get_ifrs})


class TechnicalAnalysisAgent(Agent):
    """Агент технического анализа биржевых данных."""

    def __init__(self, ai_service: AIService, moex_service: Optional[MOEXService] = None):
        super().__init__("Технический аналитик", "изучает графики и индикаторы", ai_service)
        self.moex_service = moex_service or MOEXService()

    def analyze(self, ticker: str, interval: str = "day", limit: int = 30) -> str:
        def get_candles(ticker: str, interval: str = interval, limit: int = limit) -> str:
            df = self.moex_service.get_candles(ticker, interval=interval, limit=limit)
            return df.to_csv(index=False)

        tools = [
            {
                "type": "function",
                "function": {
                    "name": "get_candles",
                    "description": "Получить котировки MOEX",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "ticker": {"type": "string"},
                            "interval": {"type": "string", "default": interval},
                            "limit": {"type": "integer", "default": limit},
                        },
                        "required": ["ticker"],
                    },
                },
            }
        ]
        system = (
            "Ты технический аналитик. Вызови get_candles для загрузки котировок "
            "и оцени тренд и уровни."
        )
        user = f"Проанализируй {ticker}."
        return self._ask_with_tools(system, user, tools, {"get_candles": get_candles})


class SocialMediaAgent(Agent):
    """Анализ постов в соцсетях."""

    def __init__(self, ai_service: AIService, news_service: Optional[NewsService] = None):
        super().__init__("Аналитик соцсетей", "оценивает настроение инвесторов", ai_service)
        self.news_service = news_service or NewsService()

    def analyze(self, ticker: str) -> str:
        def get_posts(ticker: str) -> str:
            posts = self.news_service.get_ticker_news(ticker)
            return "\n".join(posts)

        tools = [
            {
                "type": "function",
                "function": {
                    "name": "get_posts",
                    "description": "Получить посты инвесторов по тикеру",
                    "parameters": {
                        "type": "object",
                        "properties": {"ticker": {"type": "string"}},
                        "required": ["ticker"],
                    },
                },
            }
        ]
        system = (
            "Ты аналитик соцсетей. Используй get_posts для загрузки сообщений "
            "и оцени их тональность."
        )
        user = f"Оцени настроение по {ticker}."
        return self._ask_with_tools(system, user, tools, {"get_posts": get_posts})


class NewsAnalysisAgent(Agent):
    """Анализ рыночных новостей."""

    def __init__(self, ai_service: AIService, news_service: Optional[NewsService] = None):
        super().__init__("Новостной аналитик", "собирает и оценивает новости", ai_service)
        self.news_service = news_service or NewsService()

    def analyze(self, ticker: str) -> str:
        def get_news() -> str:
            news = self.news_service.get_market_news()
            return "\n".join(news)

        tools = [
            {
                "type": "function",
                "function": {
                    "name": "get_news",
                    "description": "Получить рыночные новости",
                    "parameters": {"type": "object", "properties": {}, "required": []},
                },
            }
        ]
        system = (
            "Ты новостной аналитик. Используй get_news для загрузки новостей и "
            "оцени их влияние на акции."
        )
        user = f"Проанализируй новости для {ticker}."
        return self._ask_with_tools(system, user, tools, {"get_news": lambda: get_news()})


class FundManagerAgent(Agent):
    """Агент, объединяющий выводы и формирующий решение."""

    def decide(self, ticker: str, insights: Dict[str, str]) -> str:
        parts = [f"{k}: {v}" for k, v in insights.items()]
        summary = "\n\n".join(parts)
        system = (
            "Ты управляющий фондом. На основе данных агентов дай решение: "
            "КУПИТЬ/ДЕРЖАТЬ/ПРОДАВАТЬ и краткое обоснование."
        )
        user = f"Информация по {ticker}:\n{summary}"
        return self._ask(system, user)


class CriticAgent(Agent):
    """Критик, проверяющий вывод управляющего."""

    def review(self, ticker: str, decision: str) -> str:
        system = "Ты критик. Проверь логичность и риски решения."
        user = f"Решение по {ticker}:\n{decision}"
        return self._ask(system, user)


class PortfolioAgentOrchestrator:
    """Оркестратор мультиагентного анализа."""

    def __init__(self, ai_service: Optional[AIService] = None):
        self.ai_service = ai_service or AIService()
        self.fundamental = FundamentalAnalysisAgent(self.ai_service)
        self.technical = TechnicalAnalysisAgent(self.ai_service)
        self.social = SocialMediaAgent(self.ai_service)
        self.news = NewsAnalysisAgent(self.ai_service)
        self.manager = FundManagerAgent("Управляющий фондом", "принимает решения", self.ai_service)
        self.critic = CriticAgent("Критик", "оценивает решения", self.ai_service)

    def analyze_ticker(self, ticker: str) -> Dict[str, str]:
        """Проводит полный цикл обсуждения для тикера."""
        insights: Dict[str, str] = {}
        insights["fundamental"] = self.fundamental.analyze(ticker)
        insights["technical"] = self.technical.analyze(ticker)
        insights["social"] = self.social.analyze(ticker)
        insights["news"] = self.news.analyze(ticker)

        decision = self.manager.decide(ticker, insights)
        critique = self.critic.review(ticker, decision)

        insights["decision"] = decision
        insights["critique"] = critique
        return insights
