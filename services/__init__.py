__all__ = [
    "AIService",
    "NewsService",
    "MOEXService",
    "IFRSService",
    "RecommendationDB",
    "BacktestService",
]


def __getattr__(name):
    if name == "AIService":
        from .ai_service import AIService
        return AIService
    if name == "NewsService":
        from .news_service import NewsService
        return NewsService
    if name == "MOEXService":
        from .moex_service import MOEXService
        return MOEXService
    if name == "IFRSService":
        from .ifrs_service import IFRSService
        return IFRSService
    if name == "RecommendationDB":
        from .db_service import RecommendationDB
        return RecommendationDB
    if name == "BacktestService":
        from .backtest_service import BacktestService
        return BacktestService
    raise AttributeError(f"module {__name__} has no attribute {name}")
