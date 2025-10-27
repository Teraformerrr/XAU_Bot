import numpy as np
import pandas as pd
from scipy.stats import skew, kurtosis


def historical_cvar(returns: pd.Series, alpha: float = 0.95) -> float:
    """Compute historical Conditional Value at Risk (CVaR / Expected Shortfall)."""
    r = returns.dropna().sort_values()
    if r.empty:
        return np.nan
    cutoff_index = int((1 - alpha) * len(r))
    tail = r.iloc[:max(cutoff_index, 1)]
    return tail.mean() if len(tail) > 0 else np.nan


def tail_stats(returns: pd.Series) -> dict:
    """Compute tail metrics: skewness and kurtosis."""
    r = returns.dropna()
    if r.empty:
        return {"skew": np.nan, "kurtosis": np.nan}
    return {
        "skew": float(skew(r, bias=False)),
        "kurtosis": float(kurtosis(r, fisher=True, bias=False))
    }
