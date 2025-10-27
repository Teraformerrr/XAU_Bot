"""
XAU_Bot — Phase 2 / Step 2
Ornstein–Uhlenbeck (OU) Mean Reversion Model

File: bot/models/ou_model.py
Author: Mohamed Jamshed

Purpose
-------
Detect when price deviates from its equilibrium and is likely to revert.
Implements the Ornstein–Uhlenbeck process:
    dX_t = θ(μ − X_t)dt + σ dW_t
where
  • μ = long-term mean (fair value)
  • θ = speed of reversion (0 → no pull, large → strong pull)
  • σ = volatility of the noise
"""

from __future__ import annotations
import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import Optional


# ---------------------------------------------------------------------
# Parameters container
@dataclass
class OUParams:
    theta: float   # speed of reversion
    mu: float      # long-term mean
    sigma: float   # volatility


# ---------------------------------------------------------------------
class OUModel:
    """Estimate and use an Ornstein–Uhlenbeck process on price data."""

    def __init__(self, prices: pd.Series):
        self.prices = pd.Series(prices).dropna().astype(float)
        self.params: Optional[OUParams] = None

    # -----------------------------------------------------------------
    def fit(self) -> OUParams:
        """Estimate θ, μ, σ from discrete-time regression."""
        x = self.prices.values
        x_lag = x[:-1]
        x_curr = x[1:]
        dx = x_curr - x_lag

        n = len(x_lag)
        if n < 10:
            raise ValueError("Need at least 10 data points to fit OU model")

        # Linear regression ΔX = α + β X_{t−1}
        X = np.vstack([np.ones(n), x_lag]).T
        beta = np.linalg.lstsq(X, dx, rcond=None)[0]
        a, b = beta

        dt = 1.0  # one bar per step
        theta = -np.log(1 + b) / dt
        mu = a / (1 - np.exp(-theta))
        residuals = dx - (a + b * x_lag)
        sigma = np.std(residuals) * np.sqrt(2 * theta / (1 - np.exp(-2 * theta)))

        self.params = OUParams(theta, mu, sigma)
        return self.params

    # -----------------------------------------------------------------
    def zscore(self, current_price: float, window: int = 100) -> float:
        """Compute z-score of current price vs mean of last window prices."""
        subset = self.prices.iloc[-window:]
        mean = subset.mean()
        std = subset.std(ddof=1)
        if std == 0:
            return 0.0
        return float((current_price - mean) / std)

    # -----------------------------------------------------------------
    def signal(self, current_price: float, threshold: float = 1.5) -> str:
        """Generate BUY/SELL/HOLD signal based on z-score threshold."""
        z = self.zscore(current_price)
        if z <= -threshold:
            return f"BUY (z={z:.2f})"
        elif z >= threshold:
            return f"SELL (z={z:.2f})"
        else:
            return f"HOLD (z={z:.2f})"

    # -----------------------------------------------------------------
    def simulate(self, n_steps: int, dt: float = 1.0) -> np.ndarray:
        """Simulate a synthetic OU path using fitted parameters."""
        if self.params is None:
            raise ValueError("Model not fitted yet; call fit() first.")

        theta, mu, sigma = self.params.theta, self.params.mu, self.params.sigma
        x = np.zeros(n_steps)
        x[0] = self.prices.iloc[-1]

        for t in range(1, n_steps):
            dx = theta * (mu - x[t - 1]) * dt + sigma * np.sqrt(dt) * np.random.normal()
            x[t] = x[t - 1] + dx

        return x


# ---------------------------------------------------------------------
# Self-test when run directly
if __name__ == "__main__":
    rng = np.random.default_rng(7)
    fake_prices = 2400 + np.cumsum(rng.normal(0, 2, 500))
    series = pd.Series(fake_prices)

    model = OUModel(series)
    params = model.fit()
    print("Estimated parameters:", params)

    current = float(series.iloc[-1])
    print("Signal:", model.signal(current))

    sim_path = model.simulate(50)
    print("Simulated future prices:", sim_path[:5], "...")
