#!/usr/bin/env python3
"""
Инструмент для формирования portfolio.json на основе активных акций Московской биржи.
Получает актуальный список акций из основной торговой секции и создаёт файл портфеля.
"""

import json
import logging
from pathlib import Path

import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def get_active_shares_from_moex() -> list[dict]:
    """
    Получает список активных акций из основной секции MOEX (TQBR - акции в режиме Т+).
    
    Returns:
        Список словарей с информацией об акциях
    """
    # Используем endpoint для получения списка бумаг с рыночными данными
    url = "https://iss.moex.com/iss/engines/stock/markets/shares/securities.json"
    params = {
        "marketdata_columns": "SECID,SHORTNAME,LAST,CLOSE,VALUE,VOLUME,BOARDID",
        "marketdata_filters": [("SECBOARD", "in", "('TQBR','PRIM')")],
    }
    
    try:
        with requests.Session() as session:
            resp = session.get(url, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()
        
        marketdata = data.get("marketdata", {})
        if not marketdata.get("data"):
            return []
        
        columns = marketdata["columns"]
        rows = marketdata["data"]
        
        shares = []
        for row in rows:
            security = dict(zip(columns, row))
            ticker = security["SECID"]
            last_price = security.get("LAST") or security.get("CLOSE")
            value = security.get("VALUE", 0) or 0
            
            # Оставляем только бумаги с ценой > 0 и торгами сегодня
            if last_price and last_price > 0:
                shares.append({
                    "ticker": ticker,
                    "name": security.get("SHORTNAME", ""),
                    "price": float(last_price),
                    "turnover": float(value) if value else 0,
                })
        
        # Сортируем по объёму торгов (ликвидности)
        shares.sort(key=lambda x: x["turnover"], reverse=True)
        return shares
        
    except Exception as e:
        logger.error(f"Failed to fetch active shares: {e}")
        raise


def get_imoex_constituents_alternative() -> list[str]:
    """
    Альтернативный способ получения состава индекса IMOEX.
    Использует публичные данные о весах акций в индексе.
    
    Примечание: MOEX не предоставляет прямой API для получения состава индекса,
    поэтому используем основные ликвидные бумаги как аппроксимацию.
    """
    # Основные бумаги IMOEX по ликвидности (обновляется периодически)
    # Это ядро индекса - около 40-50 наиболее ликвидных акций
    base_tickers = [
        "LKOH", "SBER", "GAZP", "NVTK", "YNDX", "ROSN", "GMKN", "TATN",
        "SNGS", "IRKT", "VTBR", "URKA", "POLY", "ALRS", "MTSS", "AFKS",
        "MGNT", "PLZL", "NLMK", "CHMF", "RTKM", "HYDR", "MOEX", "RUAL",
        "TKOG", "FLOT", "PIKK", "SGZH", "KRKNP", "AFLT", "MAGN", "BSPB",
        "TCSG", "OZON", "CBOM", "RNFT", "TRMK", "UPRO", "PHOR", "SELG",
        "GCHE", "LSRG", "DSKY", "VSMO", "AKRN", "MDMG", "STSB", "TGKD",
        "TGKB", "TGKC", "MSNG", "MRKH", "MRKK", "MRKU", "MRKY", "MRKV",
        "MRKS", "TATNP", "SNGSP", "BANEP", "POASP", "NKHP", "KMAZ",
        "NAUK", "HEAD", "ITEO", "VGZR", "HHRU", "RBIO", "ETLN", "TLKR",
        "LEAS", "RUSI", "CPSB", "NSVZ", "CHGZ", "KROT", "SMLT", "UNCM",
        "ABRD", "TRCH", "KAZT", "KAZTP", "ROLO", "CNTL", "MTLR", "MTLRP",
        "EELN", "PGTK", "IMBP", "MBNK", "PETR", "PETRP", "BRZL", "SFIN",
        "DGHC", "MEDS", "INVK", "INVKP", "RASP", "TASBP", "TASBPP", "BELU",
        "VGSB", "VGSBP", "ORUP", "ORUPP", "SARE", "SAREP", "FEES", "FESH",
        "MRSB", "MRSC", "MSRS", "MSTT", "MVTG", "NFAZ", "NKSH", "NREF",
        "OMZZP", "PRFN", "RAVN", "SAGO", "SAGOP", "SAMT", "SBSP", "SDCN",
        "SHES", "SHESP", "SIBN", "SMEE", "SRGZ", "SVET", "SYRG", "TAAT",
        "TAMT", "TDOR", "TERK", "TGLK", "THKD", "TMRS", "TNSE", "TORS",
        "TOSNP", "TRMK", "TTLK", "UWGN", "VRSB", "VRSBP", "VSMO", "YAKG",
        "ZILL", "ZVEZ", "IRAO", "RENI", "SPIR", "KMEZ", "KRKO", "KRSB",
        "KRSBP", "KTSB", "KTSBP", "KUBN", "KUZB", "KUZBP", "LVHK", "MALR",
        "META", "MFGS", "MFGSP", "MNOD", "MOST", "MRKC", "MRKP", "MRKX",
    ]
    return base_tickers


def create_portfolio_from_moex(
    output_path: str = "portfolio.json",
    use_top_n: int | None = None,
    min_turnover: float | None = None,
    default_quantity: float = 0.0,
) -> dict:
    """
    Создаёт файл portfolio.json на основе активных акций MOEX.
    
    Args:
        output_path: Путь к выходному файлу
        use_top_n: Взять только top N акций по ликвидности (если указано)
        min_turnover: Минимальный дневной оборот в рублях (фильтр)
        default_quantity: Количество акций по умолчанию
        
    Returns:
        Словарь портфеля
    """
    logger.info("Fetching active shares from MOEX...")
    
    shares = get_active_shares_from_moex()
    logger.info(f"Found {len(shares)} active shares on MOEX")
    
    if not shares:
        raise ValueError("No shares found")
    
    # Применяем фильтры
    if min_turnover is not None:
        shares = [s for s in shares if s["turnover"] >= min_turnover]
        logger.info(f"After turnover filter: {len(shares)} shares")
    
    if use_top_n is not None:
        shares = shares[:use_top_n]
        logger.info(f"Taking top {use_top_n} shares by liquidity")
    
    # Логируем топ-10 для информации
    logger.info("Top 10 by turnover:")
    for s in shares[:10]:
        logger.info(f"  {s['ticker']}: {s['name']} - ₽{s['price']:.2f}, turnover: ₽{s['turnover']:,.0f}")
    
    # Формируем портфель
    tickers = [s["ticker"] for s in shares]
    portfolio = {ticker: default_quantity for ticker in sorted(tickers)}
    portfolio["RUB"] = 0  # Добавляем рублёвую позицию
    
    # Сохраняем в файл
    output_file = Path(output_path)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(portfolio, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Portfolio saved to {output_file.resolve()}")
    logger.info(f"Total tickers: {len(portfolio) - 1}")  # Минус RUB
    
    return portfolio


def main():
    """Точка входа для CLI использования."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Создать portfolio.json на основе активных акций MOEX"
    )
    parser.add_argument(
        "-o", "--output",
        default="portfolio.json",
        help="Путь к выходному файлу (по умолчанию: portfolio.json)"
    )
    parser.add_argument(
        "-n", "--top",
        type=int,
        default=None,
        help="Взять только top N акций по ликвидности"
    )
    parser.add_argument(
        "-q", "--quantity",
        type=float,
        default=0.0,
        help="Количество акций по умолчанию (по умолчанию: 0)"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Включить подробный вывод"
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        portfolio = create_portfolio_from_moex(
            output_path=args.output,
            use_top_n=args.top,
            default_quantity=args.quantity,
        )
        
        print(f"\n✓ Portfolio created successfully!")
        print(f"  File: {args.output}")
        print(f"  Tickers: {len(portfolio) - 1}")
        print(f"\nSample tickers: {list(portfolio.keys())[:10]}...")
        print("\nEdit the file to set actual quantities for your holdings.")
        print("Note: AGRO was delisted in Dec 2024 and is excluded automatically.")
        
    except Exception as e:
        logger.error(f"Failed to create portfolio: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
