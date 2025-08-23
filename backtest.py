from services import BacktestService

if __name__ == "__main__":
    service = BacktestService()
    stats = service.run_backtest()
    print(
        f"Всего рекомендаций: {stats['total']}, "
        f"Корректных: {stats['correct']}, "
        f"Средняя доходность: {stats['avg_return']:.2%}"
    )
