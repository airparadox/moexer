import logging
import feedparser
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from tpulse import TinkoffPulse
from utils.helpers import retry_on_failure, has_only_ticker, APIError
from config import settings

logger = logging.getLogger(__name__)

class NewsService:
    """Сервис для получения и обработки новостей"""
    
    def __init__(self):
        self.pulse = TinkoffPulse()
    
    @retry_on_failure(max_retries=settings.max_retries)
    def get_market_news(self) -> List[str]:
        """
        Получает рыночные новости с lenta.ru
        
        Returns:
            Список новостей за последние дни
            
        Raises:
            APIError: При ошибках получения новостей
        """
        try:
            feed = feedparser.parse('https://lenta.ru/rss/news')
            news_entries = []
            cutoff_time = datetime.now(timezone.utc) - timedelta(days=settings.news_days_lookback)

            for entry in feed.entries[:100]:
                try:
                    pub_date = datetime.strptime(entry.published, '%a, %d %b %Y %H:%M:%S %z')
                    if pub_date > cutoff_time:
                        news_entries.append(f"{entry.title}: {entry.summary}")
                except (ValueError, AttributeError) as e:
                    logger.warning(f"Failed to parse news entry: {e}")
                    continue

            return news_entries[:settings.max_news_items]
        except Exception as e:
            logger.error(f"Market news error: {e}")
            raise APIError(f"Failed to get market news: {e}")
    
    @retry_on_failure(max_retries=settings.max_retries)
    def get_ticker_news(self, ticker: str) -> List[str]:
        """
        Получает новости по конкретному тикеру из Tinkoff Pulse
        
        Args:
            ticker: Тикер для поиска новостей
            
        Returns:
            Список новостей по тикеру
            
        Raises:
            APIError: При ошибках получения новостей
        """
        try:
            posts = self.pulse.get_posts_by_ticker(ticker)
            texts = [
                item['content']['text'] 
                for item in posts['items']
                if 'content' in item 
                and 'text' in item['content']
                and has_only_ticker(item['content']['text'], ticker)
            ]
            return texts[:settings.max_news_items]
        except Exception as e:
            logger.error(f"News error for {ticker}: {e}")
            raise APIError(f"Failed to get news for {ticker}: {e}")