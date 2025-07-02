import asyncio
import logging
from typing import Dict, Tuple

from langgraph.graph import StateGraph, START, END
from langsmith import traceable

from models.state import State, PortfolioPosition, Portfolio, AnalysisResult
from .portfolio_analyzer import PortfolioAnalyzer

logger = logging.getLogger(__name__)

class AsyncPortfolioAnalyzer(PortfolioAnalyzer):
    """Асинхронная версия PortfolioAnalyzer с параллельной обработкой тикеров."""

    def __init__(self, max_concurrent_tasks: int = 5):
        super().__init__()
        self.semaphore = asyncio.Semaphore(max_concurrent_tasks)

    async def _analyze_single(self, chain, position: PortfolioPosition) -> Tuple[str, AnalysisResult]:
        """Анализирует один тикер асинхронно."""
        async with self.semaphore:
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
            }
            logger.info(f"Async processing {position.ticker} with quantity {position.quantity}")
            result = await asyncio.to_thread(chain.invoke, initial_state)

            recommendation = "ДЕРЖАТЬ"
            if "КУПИТЬ" in result["final_data"]:
                recommendation = "КУПИТЬ"
            elif "ПРОДАВАТЬ" in result["final_data"]:
                recommendation = "ПРОДАВАТЬ"

            analysis_result = AnalysisResult(
                ticker=position.ticker,
                recommendation=recommendation,
                confidence=0.8,
                analysis_data={
                    "market_news": result.get("market_news", ""),
                    "semantic": result.get("semantic", ""),
                    "moex_analysis": result.get("moex_data_analysis", ""),
                    "ifrs_data": result.get("ifrs_data", ""),
                    "final_decision": result.get("final_data", ""),
                },
            )
            return position.ticker, analysis_result

    async def analyze_portfolio_async(self, portfolio: Portfolio) -> Dict[str, AnalysisResult]:
        """Анализирует портфель асинхронно."""
        workflow = StateGraph(State)
        workflow.add_node("generate_market_news", self.generate_market_news)
        workflow.add_node("generate_news", self.generate_news)
        workflow.add_node("grade_news", self.grade_news)
        workflow.add_node("moex_news", self.moex_news)
        workflow.add_node("make_trade_analysis", self.make_trade_analysis)
        workflow.add_node("ifrs_analysis", self.ifrs_analysis)
        workflow.add_node("final_analysis", self.final_analysis)

        workflow.add_edge(START, "generate_market_news")
        workflow.add_edge("generate_market_news", "generate_news")
        workflow.add_edge("generate_news", "grade_news")
        workflow.add_edge("grade_news", "moex_news")
        workflow.add_edge("moex_news", "make_trade_analysis")
        workflow.add_edge("make_trade_analysis", "ifrs_analysis")
        workflow.add_edge("ifrs_analysis", "final_analysis")
        workflow.add_edge("final_analysis", END)

        chain = workflow.compile()

        tasks = [self._analyze_single(chain, position) for position in portfolio.positions]
        results = await asyncio.gather(*tasks)
        return {ticker: res for ticker, res in results}
