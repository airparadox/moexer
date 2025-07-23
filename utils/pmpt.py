"""Functions for Post-Modern Portfolio Theory metrics."""

from __future__ import annotations

import numpy as np
from typing import Iterable


def downside_risk(returns: Iterable[float], target: float = 0.0, periods_per_year: int | None = None) -> float:
    """Calculate downside risk of a return series.

    Parameters
    ----------
    returns : Iterable[float]
        Sequence of periodic returns.
    target : float, optional
        Minimum acceptable return. Defaults to ``0.0``.
    periods_per_year : int | None, optional
        If provided, annualizes the risk by ``sqrt(periods_per_year)``.

    Returns
    -------
    float
        Downside risk value.
    """
    arr = np.asarray(list(returns), dtype=float)
    downside = np.minimum(0, arr - target)
    variance = np.mean(downside ** 2)
    risk = float(np.sqrt(variance))
    if periods_per_year:
        risk *= np.sqrt(periods_per_year)
    return risk


def sortino_ratio(
    returns: Iterable[float],
    target: float = 0.0,
    risk_free: float = 0.0,
    periods_per_year: int | None = None,
) -> float:
    """Calculate Sortino ratio for a series of returns."""
    arr = np.asarray(list(returns), dtype=float)
    excess = arr - risk_free
    avg_return = float(np.mean(excess))
    dr = downside_risk(arr, target=target, periods_per_year=periods_per_year)
    if dr == 0:
        return np.nan
    return avg_return / dr


def omega_ratio(returns: Iterable[float], target: float = 0.0) -> float:
    """Calculate Omega ratio for a series of returns."""
    arr = np.asarray(list(returns), dtype=float)
    excess = arr - target
    gains = excess[excess > 0].sum()
    losses = -excess[excess < 0].sum()
    if losses == 0:
        return np.inf
    return float(gains / losses)
