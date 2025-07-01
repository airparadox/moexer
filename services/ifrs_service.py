import logging
import os
from typing import Optional
from utils.helpers import DataProcessingError, truncate_text
from config import settings

logger = logging.getLogger(__name__)

class IFRSService:
    """Сервис для работы с IFRS отчетностью"""
    
    def __init__(self, finance_dir: str = "finance"):
        self.finance_dir = finance_dir
    
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
                logger.warning(f"IFRS file for {ticker} not found at {file_path}")
                return "Отчетность МСФО не найдена"

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