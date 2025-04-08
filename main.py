import logging
from datetime import datetime, timedelta
import re
import os
import requests
import pandas as pd
from dotenv import load_dotenv
from typing_extensions import TypedDict
from langsmith import traceable
from tpulse import TinkoffPulse
import apimoex
import feedparser
from openai import OpenAI
from langgraph.graph import StateGraph, START, END
from datetime import timezone
from io import StringIO


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

pulse = TinkoffPulse()
load_dotenv()

# Инициализация DeepSeek API
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_MODEL = "deepseek-chat"
client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")

class State(TypedDict):
    ticker: str
    quantity: int
    news: str
    semantic: str
    moex_data: str
    moex_data_analysis: str
    ifrs_data: str
    final_data: str
    market_news: str

def has_only_ticker(text: str, ticker: str) -> bool:
    tickers = re.findall(r'\b[A-Z]{3,4}\b', text)
    return all(t == ticker for t in tickers) and tickers

def call_deepseek(system_prompt: str, user_prompt: str) -> str:
    """Унифицированный вызов DeepSeek API с поддержкой Context Caching"""
    try:
        response = client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=1,
            stream=False
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"DeepSeek API error: {e}")
        return "Ошибка анализа"



@traceable
def generate_market_news(state: State) -> dict:
    """Получение и анализ новостей с lenta.ru"""
    try:
        feed = feedparser.parse('https://lenta.ru/rss/news')
        news_entries = []
        # Устанавливаем временную зону UTC для корректного сравнения
        cutoff_time = datetime.now(timezone.utc) - timedelta(days=1)

        for entry in feed.entries[:100]:
            # Парсим дату публикации с учетом временной зоны
            pub_date = datetime.strptime(entry.published, '%a, %d %b %Y %H:%M:%S %z')
            if pub_date > cutoff_time:
                news_entries.append(f"{entry.title}: {entry.summary}")

        if news_entries:
            system_prompt = (
                "Аналитик рынка. Кратко оцени влияние новостей на Мосбиржу. "
                "Формат:\n1. Настрой\n2. Факторы\n3. Влияние"
            )
            user_prompt = f"Новости за сутки (первые 5):\n{news_entries[:5]}"

            analysis = call_deepseek(system_prompt, user_prompt)
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
        system_prompt = (
            "Аналитик. Кратко проанализируй новости компании. "
            "Формат:\n1. Настрой\n2. Ключевое\n3. Риски"
        )
        user_prompt = f"Новости {state['ticker']} (первые 3):\n{state['news'][:3]}"

        msg = call_deepseek(system_prompt, user_prompt)
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
        system_prompt = (
            "Теханализ. Кратко проанализируй данные. "
            "Формат:\n1. Тренд\n2. Объемы\n3. Волатильность"
        )
        # Берем только последние 30 дней для анализа
        df = pd.read_csv(StringIO(state['moex_data']))
        last_30_days = df.tail(30).to_string(index=False)
        user_prompt = f"Данные {state['ticker']} (30 дней):\n{last_30_days}"

        msg = call_deepseek(system_prompt, user_prompt)
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

        system_prompt = (
            "Аналитик отчетности. Кратко оцени МСФО. "
            "Формат:\n1. Финансы\n2. Рентабельность\n3. Долги"
        )
        # Берем только первые 2000 символов отчета
        user_prompt = f"Отчетность {state['ticker']} (фрагмент):\n{ifrs_content[:2000]}"

        msg = call_deepseek(system_prompt, user_prompt)
        return {"ifrs_data": msg}
    except Exception as e:
        logger.error(f"IFRS error {state['ticker']}: {e}")
        return {"ifrs_data": "Ошибка анализа МСФО"}

@traceable
def final_analise(state: State) -> dict:
    try:
        system_prompt = (
            "Консервативный управляющий. Рекомендация: КУПИТЬ/ДЕРЖАТЬ/ПРОДАВАТЬ\nКраткое пояснение"
        )
        user_prompt = (
            f"Анализ {state['ticker']}:\n"
            f"1. Новостной фон: {state['market_news']}\n"
            f"2. Новости компании: {state['semantic']}\n"
            f"3. Тех. анализ: {state['moex_data_analysis']}\n"
            f"4. Отчетность: {state['ifrs_data']}\n"
            "Цель: доход выше депозитов при минимальном риске."
        )

        msg = call_deepseek(system_prompt, user_prompt)
        return {"final_data": msg}
    except Exception as e:
        logger.error(f"Final error {state['ticker']}: {e}")
        return {"final_data": "Ошибка"}

def process_portfolio(portfolio: dict) -> dict:
    """Обработка портфеля акций через последовательность анализов"""
    workflow = StateGraph(State)

    # Добавляем узлы в граф
    workflow.add_node("generate_market_news", generate_market_news)
    workflow.add_node("generate_news", generate_news)
    workflow.add_node("grade_news", grade_news)
    workflow.add_node("moex_news", moex_news)
    workflow.add_node("make_trade_analysis", make_trade_analysis)
    workflow.add_node("ifrs_analysis", ifrs_analysis)
    workflow.add_node("final_analise", final_analise)

    # Определяем последовательность выполнения
    workflow.add_edge(START, "generate_market_news")
    workflow.add_edge("generate_market_news", "generate_news")
    workflow.add_edge("generate_news", "grade_news")
    workflow.add_edge("grade_news", "moex_news")
    workflow.add_edge("moex_news", "make_trade_analysis")
    workflow.add_edge("make_trade_analysis", "ifrs_analysis")
    workflow.add_edge("ifrs_analysis", "final_analise")
    workflow.add_edge("final_analise", END)

    chain = workflow.compile()
    portfolio_decisions = {}

    for ticker, quantity in portfolio.items():
        initial_state = {
            "ticker": ticker,
            "quantity": quantity,
            "news": "",
            "semantic": "",
            "moex_data": "",
            "moex_data_analysis": "",
            "ifrs_data": "",
            "market_news": "",
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
