import pytest
from main import generate_analysis_report


def test_actions_table_in_report():
    results = {
        "analysis_results": {
            "MGNT": {
                "quantity": 10,
                "recommendation": "ДЕРЖАТЬ",
                "confidence": 0.8,
                "decision": "",
                "details": {}
            },
            "SBER": {
                "quantity": 5,
                "recommendation": "КУПИТЬ",
                "confidence": 0.8,
                "decision": "",
                "details": {}
            },
        },
        "rebalancing_suggestions": {
            "MGNT": "Держать",
            "SBER": "Купить 150",
            "TRNFP": "Продать 20",
            "RUB": "Остаток 1000"
        },
        "portfolio_summary": {
            "total_positions": 2,
            "buy_recommendations": 1,
            "sell_recommendations": 1,
            "hold_recommendations": 0,
            "average_confidence": 0.8,
            "portfolio_action": "",
            "cash_rub": 1000,
        },
    }

    report = generate_analysis_report(results)
    assert "MGNT" in report
    assert "Держать" in report
    assert "SBER" in report
    assert "Купить 150" in report
    assert "TRNFP" in report
    assert "Продать 20" in report
    assert "RUB" in report
    assert "Остаток 1000" in report
