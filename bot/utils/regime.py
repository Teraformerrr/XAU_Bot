# D:\XAU_Bot\bot\utils\regime.py
from __future__ import annotations
import numpy as np
import pandas as pd

def rolling_volatility(close: pd.Series, window: int = 50) -> float:
    if len(close) < max(20, window):
        return 0.0
    # annualized-ish std proxy over last window; keep it simple and fast
    returns = close.pct_change().dropna()
    vol = returns.tail(window).std()
    return float(0.0 if np.isnan(vol) else vol)

def detect_regime(close: pd.Series, kf_slope: float | None = None) -> str:
    """
    Very light-touch regime classifier:
    - 'trend' if Kalman slope strongly non-zero or last N candles directional
    - 'range' otherwise
    """
    if kf_slope is not None and abs(kf_slope) > 1e-6:
        return "trend"
    if len(close) < 30:
        return "range"
    last = close.tail(20)
    up_moves = (last.diff() > 0).sum()
    down_moves = (last.diff() < 0).sum()
    if abs(up_moves - down_moves) >= 8:
        return "trend"
    return "range"
