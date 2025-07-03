import logging
import os
from typing import Optional

import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent

from utils.helpers import DataProcessingError, truncate_text
from config import settings

logger = logging.getLogger(__name__)

class IFRSService:
    """Сервис для работы с IFRS отчетностью"""
    
    def __init__(self, finance_dir: str = "finance"):
        self.finance_dir = finance_dir

    def fetch_ifrs_from_web(self, ticker: str) -> str:
        """Скачивает таблицу МСФО с smart-lab и переводит её в текст."""
        url = f"https://smart-lab.ru/q/{ticker}/f/y/"
        try:
            try:
                ua = UserAgent()
                headers = {"User-Agent": ua.chrome}
            except Exception:
                headers = {"User-Agent": "Mozilla/5.0"}

            response = requests.get(url, headers=headers, timeout=settings.api_timeout)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")
            table = soup.find("table")
            if not table:
                logger.warning(f"IFRS table not found on {url}")
                return "Отчетность МСФО не найдена"

            rows = []
            for tr in table.find_all("tr"):
                cells = [c.get_text(strip=True) for c in tr.find_all(["th", "td"])]
                if cells:
                    rows.append("\t".join(cells))

            text = "\n".join(rows)
            return truncate_text(text, settings.max_ifrs_content_length)
        except Exception as e:
            logger.error(f"Failed to fetch IFRS data for {ticker}: {e}")
            raise DataProcessingError(f"Failed to download IFRS data for {ticker}: {e}")
    
    def get_ifrs_data(self, ticker: str) -> str:
        """
        Получает данные IFRS отчетности для тикера
        
        Args:
            ticker: Тикер компании
            
        Returns:
            Содержимое IFRS отчета (обрезанное до максимальной длины)
            
        Raises:
            DataProcessingError: При ошибках чтения файла
        """
        try:
            file_path = os.path.join(self.finance_dir, f"{ticker}.txt")

            if not os.path.exists(file_path):
                logger.info(f"IFRS file for {ticker} not found at {file_path}, downloading")
                return self.fetch_ifrs_from_web(ticker)

            with open(file_path, 'r', encoding='utf-8') as f:
                ifrs_content = f.read()
            
            # Обрезаем содержимое до максимальной длины
            truncated_content = truncate_text(ifrs_content, settings.max_ifrs_content_length)
            
            return truncated_content
            
        except Exception as e:
            logger.error(f"IFRS error for {ticker}: {e}")
            raise DataProcessingError(f"Failed to read IFRS data for {ticker}: {e}")
    
    def has_ifrs_data(self, ticker: str) -> bool:
        """
        Проверяет наличие IFRS файла для тикера
        
        Args:
            ticker: Тикер компании
            
        Returns:
            True если файл существует, False иначе
        """
        file_path = os.path.join(self.finance_dir, f"{ticker}.txt")
        return os.path.exists(file_path)