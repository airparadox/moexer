from analyzers import PortfolioAnalyzer
from models.state import RiskProfile


def test_final_analysis_uses_weights(monkeypatch):
    analyzer = PortfolioAnalyzer()
    captured = {}

    def fake_call_model(system_prompt, user_prompt):
        if 'system' not in captured:
            captured['system'] = system_prompt
            captured['user'] = user_prompt
        return "Рекомендация: ДЕРЖАТЬ"

    monkeypatch.setattr(analyzer.ai_service, "call_model", fake_call_model)

    state = {
        "ticker": "AAA",
        "quantity": 1,
        "market_news": "news",
        "semantic": "social",
        "moex_data_analysis": "moex",
        "ifrs_data": "ifrs",
        "risk_profile": RiskProfile.BALANCED.value,
    }

    analyzer.final_analysis(state)

    assert "55%" in captured['system']
    assert "20%" in captured['system']
    assert "15%" in captured['system']
    assert "10%" in captured['system']
    assert "вес 55%" in captured['user']
