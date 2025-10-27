"""
XAU_Bot — Phase 2 / Step 3
Kalman Filter (Local Level + Trend) for Price Smoothing & State Estimation

File: bot/models/kalman_filter.py
Author: Mohamed Jamshed

Purpose
-------
Reduces noise in XAUUSD prices and estimates hidden states:
  • level (de-noised price)
  • trend (slope / direction)

Model
-----
State vector s_t = [level_t, trend_t]^T
Transition:  s_t = F * s_{t-1} + w_t,     F = [[1, 1], [0, 1]]
Observation: y_t = H * s_t + v_t,         H = [1, 0]
Noise: w_t ~ N(0, Q), v_t ~ N(0, R)
Q = diag(q_level, q_trend); R = r_obs
"""

from __future__ import annotations
import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import Optional, Tuple, Dict


# ---------------------------------------------------------------------
# Configuration dataclass
@dataclass
class KFParams:
    q_level: float = 1e-3   # process noise for level
    q_trend: float = 1e-5   # process noise for trend
    r_obs: float = 1e-2     # observation noise


# ---------------------------------------------------------------------
class KalmanTrend:
    """
    2D Kalman filter for local level + local trend (constant velocity).

    Use cases:
      - Smooth noisy OHLC close series.
      - Estimate hidden trend in gold price.
      - Produce 1-step forecasts and signals.
    """

    def __init__(self, params: KFParams | None = None):
        self.params = params or KFParams()
        self.F = np.array([[1.0, 1.0],
                           [0.0, 1.0]], dtype=float)
        self.H = np.array([[1.0, 0.0]], dtype=float)

    # -----------------------------------------------------------------
    def _filter_core(self, y: np.ndarray) -> Dict[str, np.ndarray]:
        n = len(y)
        F, H = self.F, self.H
        qL, qT, r = self.params.q_level, self.params.q_trend, self.params.r_obs
        Q = np.array([[qL, 0.0], [0.0, qT]], dtype=float)
        R = np.array([[r]], dtype=float)

        # Allocate storage
        x_pred = np.zeros((n, 2))
        P_pred = np.zeros((n, 2, 2))
        x_filt = np.zeros((n, 2))
        P_filt = np.zeros((n, 2, 2))
        K_gain = np.zeros((n, 2, 1))
        innov = np.zeros((n, 1))
        innov_var = np.zeros((n, 1))

        # Initialize
        x_filt[0] = np.array([y[0], 0.0])
        P_filt[0] = np.eye(2) * 1.0

        for t in range(1, n):
            # Predict
            x_pred[t] = F @ x_filt[t - 1]
            P_pred[t] = F @ P_filt[t - 1] @ F.T + Q

            # Innovation
            y_pred = (H @ x_pred[t].reshape(2, 1))[0, 0]
            e_t = y[t] - y_pred
            S_t = (H @ P_pred[t] @ H.T + R)[0, 0]

            # Kalman gain
            K_t = (P_pred[t] @ H.T) / S_t  # shape (2,1)

            # Update
            x_filt[t] = x_pred[t] + (K_t.flatten() * e_t)
            P_filt[t] = (np.eye(2) - K_t @ H) @ P_pred[t]

            # Save values
            K_gain[t] = K_t
            innov[t] = e_t
            innov_var[t] = S_t

        return {
            "x_pred": x_pred,
            "P_pred": P_pred,
            "x_filt": x_filt,
            "P_filt": P_filt,
            "K_gain": K_gain,
            "innov": innov,
            "innov_var": innov_var,
        }

    # -----------------------------------------------------------------
    def filter(self, prices: pd.Series) -> pd.DataFrame:
        y = pd.Series(prices).dropna().astype(float).values
        res = self._filter_core(y)

        level = res["x_filt"][:, 0]
        trend = res["x_filt"][:, 1]
        forecast = (self.H @ (self.F @ res["x_filt"].T)).flatten()

        df = pd.DataFrame({
            "filtered": level,
            "trend": trend,
            "forecast_1": forecast,
            "innov": res["innov"].flatten(),
            "innov_var": res["innov_var"].flatten(),
            "k_gain_level": res["K_gain"][:, 0, 0],
            "k_gain_trend": res["K_gain"][:, 1, 0],
        }, index=pd.RangeIndex(len(y)))
        return df

    # -----------------------------------------------------------------
    def smooth(self, prices: pd.Series) -> pd.DataFrame:
        """Backward pass smoother (Rauch–Tung–Striebel)."""
        y = pd.Series(prices).dropna().astype(float).values
        res = self._filter_core(y)
        x_filt, P_filt = res["x_filt"], res["P_filt"]
        x_pred, P_pred = res["x_pred"], res["P_pred"]
        n = len(y)

        x_smooth = np.zeros_like(x_filt)
        P_smooth = np.zeros_like(P_filt)
        x_smooth[-1] = x_filt[-1]
        P_smooth[-1] = P_filt[-1]

        for t in range(n - 2, -1, -1):
            C_t = P_filt[t] @ self.F.T @ np.linalg.pinv(P_pred[t + 1])
            x_smooth[t] = x_filt[t] + C_t @ (x_smooth[t + 1] - x_pred[t + 1])
            P_smooth[t] = P_filt[t] + C_t @ (P_smooth[t + 1] - P_pred[t + 1]) @ C_t.T

        df = pd.DataFrame({
            "level_smooth": x_smooth[:, 0],
            "trend_smooth": x_smooth[:, 1],
        }, index=pd.RangeIndex(n))
        return df

    # -----------------------------------------------------------------
    def auto_tune(self, prices: pd.Series,
                  qL_grid=(1e-6, 1e-5, 1e-4, 1e-3),
                  qT_grid=(1e-7, 1e-6, 1e-5, 1e-4),
                  r_grid=(1e-4, 1e-3, 1e-2, 1e-1)) -> KFParams:
        """Find good Q,R by minimizing forecast RMSE."""
        y = pd.Series(prices).dropna().astype(float).values
        best = (None, np.inf)
        orig = self.params

        for qL in qL_grid:
            for qT in qT_grid:
                for r in r_grid:
                    self.params = KFParams(qL, qT, r)
                    res = self._filter_core(y)
                    x_filt = res["x_filt"]
                    forecast = (self.H @ (self.F @ x_filt.T)).flatten()
                    err = y - forecast
                    rmse = np.sqrt(np.mean(err[1:] ** 2))
                    if rmse < best[1]:
                        best = (KFParams(qL, qT, r), rmse)

        self.params = best[0] or orig
        return self.params

    # -----------------------------------------------------------------
    @staticmethod
    def signals(filtered_df: pd.DataFrame,
                trend_window: int = 50,
                z_thresh: float = 1.2) -> pd.Series:
        """Create BUY/SELL/HOLD based on z-score of trend."""
        tr = pd.Series(filtered_df["trend"]).astype(float)
        z = (tr - tr.rolling(trend_window).mean()) / tr.rolling(trend_window).std(ddof=1)
        z = z.fillna(0.0)
        sig = pd.Series("HOLD", index=tr.index)
        sig[z >= z_thresh] = "SELL"
        sig[z <= -z_thresh] = "BUY"
        return sig


# ---------------------------------------------------------------------
# Self-test section
if __name__ == "__main__":
    rng = np.random.default_rng(42)
    n = 500
    base = 2400 + np.linspace(0, 25, n) + rng.normal(0, 2, n)
    s = pd.Series(base)

    kf = KalmanTrend()
    tuned = kf.auto_tune(s)
    print("Tuned params:", tuned)

    f = kf.filter(s)
    print(f.head())

    sm = kf.smooth(s)
    print(sm.head())

    sig = KalmanTrend.signals(f)
    print(sig.value_counts())
