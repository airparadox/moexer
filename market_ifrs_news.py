import logging
from datetime import datetime, timedelta
import re
import os
import requests
import pandas as pd
from dotenv import load_dotenv
from langchain_gigachat import GigaChat
from typing_extensions import TypedDict
from langsmith import traceable
from tpulse import TinkoffPulse
from langchain_ollama import OllamaLLM
import apimoex
import feedparser  # Добавлено для работы с RSS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

pulse = TinkoffPulse()
load_dotenv()
GIGACHAT_CREDENTIALS = os.getenv("GIGACHAT_CREDENTIALS")
LLM_MODEL = os.getenv("LLM_MODEL", "GigaChat")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", 0))

# llm = OllamaLLM(model="qwen2.5:14b", temperature=LLM_TEMPERATURE)
llm = GigaChat(
    credentials=GIGACHAT_CREDENTIALS,
    model=LLM_MODEL,
    temperature=LLM_TEMPERATURE,
    verify_ssl_certs=False
)



# qwen2.5:14b
class State(TypedDict):
    ticker: str
    quantity: int
    news: str
    semantic: str
    moex_data: str
    moex_data_analysis: str
    ifrs_data: str
    final_data: str
    market_news: str  # Добавлено для общего новостного фона

def has_only_ticker(text: str, ticker: str) -> bool:
    tickers = re.findall(r'\b[A-Z]{3,4}\b', text)
    return all(t == ticker for t in tickers) and tickers

@traceable
def generate_market_news(state: State) -> dict:
    """Получение и анализ новостей с lenta.ru"""
    try:
        # Парсинг RSS-ленты lenta.ru
        feed = feedparser.parse('https://lenta.ru/rss/news')
        # Берем последние 10 новостей за сутки
        news_entries = []
        from datetime import timezone  # Добавляем импорт
        cutoff_time = datetime.now(timezone.utc) - timedelta(days=1)  # Добавляем UTC

        for entry in feed.entries[:100]:
            pub_date = datetime.strptime(entry.published, '%a, %d %b %Y %H:%M:%S %z')
            if pub_date > cutoff_time:
                news_entries.append(f"{entry.title}: {entry.summary}")

        # Анализ новостей через LLM
        if news_entries:
            analysis = llm.invoke(
                f"Анализ новостей за сутки: {news_entries}\n"
                "Оцени влияние на торговлю на Московской бирже:\n"
                "1. Общий настрой (позитивный/негативный/нейтральный)\n"
                "2. Ключевые факторы\n"
                "3. Потенциальное влияние на индекс MOEX\n"
                "Формат:\n1. Общий настрой\n2. Ключевые факторы\n3. Потенциальное влияние"
            )
            return {"market_news": analysis}
        return {"market_news": "Недостаточно свежих новостей для анализа"}
    except Exception as e:
        logger.error(f"Market news error: {e}")
        return {"market_news": "Ошибка при анализе новостей"}

@traceable
def generate_news(state: State) -> dict:
    try:
        posts = pulse.get_posts_by_ticker(state['ticker'])
        texts = [item['content']['text'] for item in posts['items']
                 if 'content' in item and 'text' in item['content']
                 and has_only_ticker(item['content']['text'], state['ticker'])]
        return {"news": texts}
    except Exception as e:
        logger.error(f"News error {state['ticker']}: {e}")
        return {"news": []}

@traceable
def grade_news(state: State) -> dict:
    try:
        msg = llm.invoke(
            f"Анализ новостей {state['ticker']}: {state['news']}\n"
            "Оцени:\n1. Настрой\n2. Темы\n3. Перспективы\n4. Риски\n"
            "Формат:\n1. Настрой\n2. Темы\n3. Перспективы\n4. Риски"
        )
        return {"semantic": msg}
    except Exception as e:
        logger.error(f"Grade error {state['ticker']}: {e}")
        return {"semantic": "Ошибка"}

@traceable
def moex_news(state: State) -> dict:
    try:
        end = datetime.now()
        start = end - timedelta(days=180)
        with requests.Session() as session:
            data = apimoex.get_board_history(
                session, state['ticker'],
                start=start.strftime('%Y-%m-%d'),
                end=end.strftime('%Y-%m-%d')
            )
            if not data: raise ValueError("Нет данных")
            df = pd.DataFrame(data)[['TRADEDATE', 'CLOSE', 'VOLUME', 'VALUE']]
            return {"moex_data": df.to_string(index=False)}
    except Exception as e:
        logger.error(f"MOEX error {state['ticker']}: {e}")
        return {"moex_data": "Ошибка"}

@traceable
def make_trade_analysis(state: State) -> dict:
    try:
        msg = llm.invoke(
            f"Анализ {state['ticker']} за 180 дней: {state['moex_data']}\n"
            "Оцени:\n2.1 Тренды\n2.2 Импульс\n2.3 Волатильность\n"
            "Формат:\nИндикатор - значение"
        )
        return {"moex_data_analysis": msg}
    except Exception as e:
        logger.error(f"Trade error {state['ticker']}: {e}")
        return {"moex_data_analysis": "Ошибка"}

@traceable
def ifrs_analysis(state: State) -> dict:
    try:
        file_path = os.path.join("finance", f"{state['ticker']}.txt")
        if not os.path.exists(file_path):
            logger.warning(f"Файл МСФО для {state['ticker']} не найден")
            return {"ifrs_data": "Отчетность МСФО не найдена"}

        with open(file_path, 'r', encoding='utf-8') as f:
            ifrs_content = f.read()

        msg = llm.invoke(
            f"Анализ отчетности МСФО {state['ticker']}:\n{ifrs_content}\n"
            "Оцени:\n1. Финансовая устойчивость\n2. Рентабельность\n3. Ликвидность\n4. Долговая нагрузка\n"
            "Формат:\n1. Финансовая устойчивость\n2. Рентабельность\n3. Ликвидность\n4. Долговая нагрузка"
        )
        return {"ifrs_data": msg}
    except Exception as e:
        logger.error(f"IFRS error {state['ticker']}: {e}")
        return {"ifrs_data": "Ошибка анализа МСФО"}

@traceable
def final_analise(state: State) -> dict:
    try:
        msg = llm.invoke(
            f"Анализ {state['ticker']}:\n"
            f"1. Общий новостной фон: {state['market_news']}\n"
            f"2. Новости компании: {state['semantic']}\n"
            f"3. Тех. анализ: {state['moex_data_analysis']}\n"
            f"4. Отчетность МСФО: {state['ifrs_data']}\n"
            "Консервативный инвестор, 5+ лет, доход выше депозитов.\n"
            "Формат: КУПИТЬ/ДЕРЖАТЬ/ПРОДАВАТЬ\nПояснение"
        )
        return {"final_data": msg}
    except Exception as e:
        logger.error(f"Final error {state['ticker']}: {e}")
        return {"final_data": "Ошибка"}

def process_portfolio(portfolio: dict) -> dict:
    from langgraph.graph import StateGraph, START, END

    portfolio_decisions = {}
    workflow = StateGraph(State)
    workflow.add_node("generate_market_news", generate_market_news)  # Новый узел
    workflow.add_node("generate_news", generate_news)
    workflow.add_node("grade_news", grade_news)
    workflow.add_node("moex_news", moex_news)
    workflow.add_node("make_trade_analysis", make_trade_analysis)
    workflow.add_node("ifrs_analysis", ifrs_analysis)
    workflow.add_node("final_analise", final_analise)
    workflow.add_edge(START, "generate_market_news")  # Начинаем с общего фона
    workflow.add_edge("generate_market_news", "generate_news")
    workflow.add_edge("generate_news", "grade_news")
    workflow.add_edge("grade_news", "moex_news")
    workflow.add_edge("moex_news", "make_trade_analysis")
    workflow.add_edge("make_trade_analysis", "ifrs_analysis")
    workflow.add_edge("ifrs_analysis", "final_analise")
    workflow.add_edge("final_analise", END)

    chain = workflow.compile()

    for ticker, quantity in portfolio.items():
        initial_state = {
            "ticker": ticker,
            "quantity": quantity,
            "news": "",
            "semantic": "",
            "moex_data": "",
            "moex_data_analysis": "",
            "ifrs_data": "",
            "market_news": "",  # Добавлено в начальное состояние
            "final_data": ""
        }

        logger.info(f"Processing {ticker} with quantity {quantity}")
        result = chain.invoke(initial_state)
        portfolio_decisions[ticker] = {
            "quantity": quantity,
            "decision": result["final_data"]
        }

    return portfolio_decisions

@traceable
def suggest_rebalancing(decisions: dict) -> dict:
    rebalancing_suggestions = {}
    total_positions = len(decisions)
    target_weight = 1.0 / total_positions if total_positions > 0 else 0

    for ticker, data in decisions.items():
        decision_text = data["decision"]
        current_quantity = data["quantity"]

        if "КУПИТЬ" in decision_text:
            rebalancing_suggestions[ticker] = f"Увеличить позицию (текущий объем: {current_quantity})"
        elif "ПРОДАВАТЬ" in decision_text:
            rebalancing_suggestions[ticker] = f"Уменьшить позицию (текущий объем: {current_quantity})"
        else:  # ДЕРЖАТЬ
            rebalancing_suggestions[ticker] = f"Сохранить позицию (текущий объем: {current_quantity})"

    return rebalancing_suggestions

if __name__ == "__main__":
    portfolio = {
        'MGNT': 13,
        'UNAC': 36000,
        'TRNFP': 111
    }

    decisions = process_portfolio(portfolio)
    rebalancing = suggest_rebalancing(decisions)

    print("\nРешения по портфелю:")
    for ticker, data in decisions.items():
        print(f"{ticker}:")
        print(f"Текущий объем: {data['quantity']}")
        print(f"Решение: {data['decision']}")
        print(f"Рекомендация: {rebalancing[ticker]}\n")