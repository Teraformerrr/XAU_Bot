import numpy as np
import pandas as pd


def _annualize_factor(freq: str) -> float:
    """Return annualization factor based on frequency string."""
    freq = freq.lower()
    if freq.endswith('min'):
        return 252 * 24 * 60  # trading minutes in a year
    if freq.endswith('h'):
        return 252 * 24
    if freq.endswith('d'):
        return 252
    if freq.endswith('w'):
        return 52
    if freq.endswith('m'):
        return 12
    return 1.0


# ----------------------------------------------------------------------
def sharpe_ratio(returns: pd.Series, rf_annual: float = 0.02, freq: str = '1min') -> float:
    """Compute annualized Sharpe ratio."""
    r = returns.dropna()
    if r.empty:
        return np.nan

    rf = (1 + rf_annual) ** (1 / _annualize_factor(freq)) - 1
    excess = r - rf
    ann_factor = np.sqrt(_annualize_factor(freq))

    if excess.std() == 0:
        return np.nan

    return (excess.mean() / excess.std()) * ann_factor


# ----------------------------------------------------------------------
def sortino_ratio(returns: pd.Series, rf_annual: float = 0.02, freq: str = '1min') -> float:
    """Compute annualized Sortino ratio."""
    r = returns.dropna()
    if r.empty:
        return np.nan

    rf = (1 + rf_annual) ** (1 / _annualize_factor(freq)) - 1
    downside = r[r < 0]
    if downside.std() == 0:
        return np.nan

    ann_factor = np.sqrt(_annualize_factor(freq))
    return ((r.mean() - rf) / downside.std()) * ann_factor


# ----------------------------------------------------------------------
def information_ratio(returns: pd.Series, benchmark: pd.Series, freq: str = '1min') -> float:
    """Compute annualized Information Ratio against benchmark."""
    r = returns.dropna()
    b = benchmark.dropna()
    if r.empty or b.empty:
        return np.nan

    diff = r.align(b, join='inner')[0] - b.align(r, join='inner')[0]
    if diff.std() == 0:
        return np.nan

    ann_factor = np.sqrt(_annualize_factor(freq))
    return (diff.mean() / diff.std()) * ann_factor


# ----------------------------------------------------------------------
def max_drawdown(x: pd.Series) -> float:
    """Compute maximum drawdown from an equity curve or cumulative return series."""
    if x is None or len(x) == 0:
        return np.nan

    roll_max = x.cummax()
    drawdown = (x - roll_max) / roll_max
    return drawdown.min()
