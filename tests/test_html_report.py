import pytest
from main import generate_html_report


def test_generate_html_report_contains_tables():
    results = {
        "analysis_results": {
            "MGNT": {
                "quantity": 10,
                "decision": "Держать",
                "recommendation": "Держать",
                "confidence": 0.8,
                "details": {"pmpt": {"downside_risk": 0.1, "sortino_ratio": 1.2, "omega_ratio": 1.5}},
            }
        },
        "rebalancing_suggestions": {"MGNT": "Держать"},
        "portfolio_summary": {
            "total_positions": 1,
            "buy_recommendations": 0,
            "sell_recommendations": 0,
            "hold_recommendations": 1,
            "average_confidence": 0.8,
            "portfolio_action": "Держать",
        },
    }

    html = generate_html_report(results)
    assert "<html" in html
    assert "<table" in html
    assert "MGNT" in html
    assert "Держать" in html
