import importlib.util
import sys
import types
from pathlib import Path

import pandas as pd

from models import AnalysisResult, Portfolio

services_module = types.ModuleType("services")
spec_moex = importlib.util.spec_from_file_location(
    "moex_service", Path(__file__).resolve().parents[1] / "services" / "moex_service.py"
)
moex_module = importlib.util.module_from_spec(spec_moex)
spec_moex.loader.exec_module(moex_module)  # type: ignore[arg-type]
services_module.moex_service = moex_module
sys.modules["services"] = services_module
sys.modules["services.moex_service"] = moex_module

spec = importlib.util.spec_from_file_location(
    "rebalancing_analyzer", Path(__file__).resolve().parents[1] / "analyzers" / "rebalancing_analyzer.py"
)
rebalancing_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rebalancing_module)  # type: ignore[arg-type]
RebalancingAnalyzer = rebalancing_module.RebalancingAnalyzer


def test_final_decision_aligns_with_rebalancing():
    portfolio = Portfolio.from_dict({"AAA": 0, "RUB": 1000})
    results = {
        "AAA": AnalysisResult(
            ticker="AAA", recommendation="КУПИТЬ", confidence=1.0, analysis_data={}
        )
    }

    price_df = pd.DataFrame({"price": [100.0]}, index=["AAA"])
    rebalancer = RebalancingAnalyzer(price_getter=lambda ts: price_df.loc[ts])
    suggestions = rebalancer.suggest_rebalancing(results, portfolio)

    assert suggestions["AAA"].startswith("Купить")

