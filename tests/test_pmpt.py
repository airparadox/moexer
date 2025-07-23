import numpy as np
import pytest

from utils.pmpt import downside_risk, sortino_ratio, omega_ratio, pmpt_metrics


def test_downside_risk():
    returns = [0.05, -0.02, 0.03, -0.01, 0.04]
    expected = np.sqrt(((-0.02) ** 2 + (-0.01) ** 2) / 5)
    assert downside_risk(returns) == pytest.approx(expected)


def test_sortino_ratio():
    returns = [0.1, 0.0, -0.05, 0.07]
    avg = np.mean(returns)
    dr = downside_risk(returns)
    assert sortino_ratio(returns) == pytest.approx(avg / dr)


def test_omega_ratio():
    returns = [0.1, -0.02, 0.04, -0.01]
    gains = 0.1 + 0.04
    losses = 0.02 + 0.01
    assert omega_ratio(returns) == pytest.approx(gains / losses)


def test_pmpt_metrics():
    returns = [0.05, 0.0, -0.05, 0.07]
    metrics = pmpt_metrics(returns)
    assert set(metrics.keys()) == {"downside_risk", "sortino_ratio", "omega_ratio"}
    assert metrics["sortino_ratio"] == pytest.approx(sortino_ratio(returns))
