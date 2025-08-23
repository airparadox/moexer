from datetime import datetime

from services.db_service import RecommendationDB
from models import RecommendationRecord


def test_save_and_fetch(tmp_path):
    db_path = tmp_path / "rec.db"
    db = RecommendationDB(db_path)
    record = RecommendationRecord(
        ticker="SBER",
        recommendation="КУПИТЬ",
        confidence=0.9,
        price=100.0,
        timestamp=datetime(2024, 1, 1),
    )
    db.save(record)
    records = db.fetch_all()
    db.close()

    assert len(records) == 1
    assert records[0].ticker == "SBER"
    assert records[0].recommendation == "КУПИТЬ"


def test_fetch_latest(tmp_path):
    db_path = tmp_path / "rec.db"
    db = RecommendationDB(db_path)
    first = RecommendationRecord(
        ticker="SBER",
        recommendation="КУПИТЬ",
        confidence=0.8,
        price=90.0,
        timestamp=datetime(2024, 1, 1, 10, 0, 0),
    )
    second = RecommendationRecord(
        ticker="SBER",
        recommendation="ПРОДАВАТЬ",
        confidence=0.6,
        price=110.0,
        timestamp=datetime(2024, 1, 2, 10, 0, 0),
    )
    db.save(first)
    db.save(second)
    latest = db.fetch_latest("sber")
    db.close()

    assert latest is not None
    assert latest.recommendation == "ПРОДАВАТЬ"
    assert latest.timestamp == datetime(2024, 1, 2, 10, 0, 0)
