import importlib

from models.state import RiskProfile


def test_final_analysis_uses_weights(monkeypatch, tmp_path):
    config_file = tmp_path / "modules.csv"
    config_file.write_text(
        "ifrs,1,0.4\nmarket_news,1,0.3\nmoex,1,0.2\nsocial,1,0.1\n",
        encoding="utf-8",
    )

    monkeypatch.setenv("MODULE_CONFIG_FILE", str(config_file))
    import config as cfg
    importlib.reload(cfg)
    cfg.get_modules_config.cache_clear()
    import analyzers.portfolio_analyzer as pa
    importlib.reload(pa)
    from analyzers.portfolio_analyzer import PortfolioAnalyzer

    analyzer = PortfolioAnalyzer()
    captured = {}

    def fake_call_model(system_prompt, user_prompt):
        if "system" not in captured:
            captured["system"] = system_prompt
            captured["user"] = user_prompt
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

    assert "40%" in captured["system"]
    assert "30%" in captured["system"]
    assert "20%" in captured["system"]
    assert "10%" in captured["system"]
    assert "вес 40%" in captured["user"]
