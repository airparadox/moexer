import sqlite3
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from models import RecommendationRecord


class RecommendationDB:
    """Простой сервис для сохранения рекомендаций в SQLite."""

    def __init__(self, db_path: str = "recommendations.db") -> None:
        self.db_path = Path(db_path)
        self.conn = sqlite3.connect(str(self.db_path))
        self._create_table()

    def _create_table(self) -> None:
        cursor = self.conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS recommendations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                recommendation TEXT NOT NULL,
                confidence REAL NOT NULL,
                price REAL NOT NULL,
                timestamp TEXT NOT NULL
            )
            """
        )
        self.conn.commit()

    def save(self, record: RecommendationRecord) -> None:
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO recommendations (ticker, recommendation, confidence, price, timestamp)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                record.ticker,
                record.recommendation,
                record.confidence,
                record.price,
                record.timestamp.isoformat(),
            ),
        )
        self.conn.commit()

    def fetch_all(self) -> List[RecommendationRecord]:
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT ticker, recommendation, confidence, price, timestamp FROM recommendations"
        )
        rows = cursor.fetchall()
        records = [
            RecommendationRecord(
                ticker=row[0],
                recommendation=row[1],
                confidence=row[2],
                price=row[3],
                timestamp=datetime.fromisoformat(row[4]),
            )
            for row in rows
        ]
        return records

    def fetch_latest(self, ticker: str) -> Optional[RecommendationRecord]:
        """Возвращает последнюю рекомендацию для указанного тикера."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT ticker, recommendation, confidence, price, timestamp
            FROM recommendations
            WHERE ticker = ?
            ORDER BY timestamp DESC
            LIMIT 1
            """,
            (ticker.upper(),),
        )
        row = cursor.fetchone()
        if not row:
            return None
        return RecommendationRecord(
            ticker=row[0],
            recommendation=row[1],
            confidence=row[2],
            price=row[3],
            timestamp=datetime.fromisoformat(row[4]),
        )

    def close(self) -> None:
        self.conn.close()
