import argparse
from services import RecommendationDB


def format_record(rec):
    return (
        f"{rec.timestamp:%Y-%m-%d %H:%M} {rec.ticker} "
        f"{rec.recommendation} ({rec.confidence:.2f}) @ {rec.price:.2f}"
    )


def main():
    parser = argparse.ArgumentParser(
        description="Показывает сохранённые рекомендации из локальной БД"
    )
    parser.add_argument(
        "-t",
        "--ticker",
        help="Показать только последнюю рекомендацию для тикера",
    )
    args = parser.parse_args()
    db = RecommendationDB()
    try:
        if args.ticker:
            rec = db.fetch_latest(args.ticker)
            if rec:
                print(format_record(rec))
            else:
                print(f"Рекомендаций для {args.ticker} не найдено")
        else:
            for rec in db.fetch_all():
                print(format_record(rec))
    finally:
        db.close()


if __name__ == "__main__":
    main()
