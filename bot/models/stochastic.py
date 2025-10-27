"""
XAU_Bot — Phase 2 / Step 1
Stochastic Calculus Module

File: bot/models/stochastic.py
Author: Mohamed Jamshed (project owner)

Purpose
-------
This module provides stochastic-process utilities used across the XAU_Bot intelligence layer.
It includes:
  • Brownian Motion (discrete-time) generator
  • Geometric Brownian Motion (GBM) simulator for price paths
  • Volatility & drift estimators (realized, EWMA) calibrated from OHLCV/close data
  • Step-wise sampling for live use (produce the next price from the current one)
  • Multi-path simulations for stress testing (risk & scenario analysis)

Design Notes
------------
- All time is handled in trading "steps" (e.g., 1m, 5m, 1h). You specify `dt` in YEARS for the step.
  Example: for 1-minute bars, dt = 1 / (252 * 6.5 * 60) for US equities; for 24/5 FX, a pragmatic
  approximation is dt = minutes_per_bar / (365 * 24 * 60). We provide helper `dt_from_minutes_fx()`.
- Calibrate drift (mu) and volatility (sigma) from log-returns of your price series.
- Safe defaults + robust guards for NaNs / short series.

Dependencies
------------
- numpy, pandas

This file is self-contained: it will try to use `utils.math_tools` if available; otherwise it falls
back to local helpers for log-returns, z-scores, and annualization.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple
import math
import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Optional import from Phase 2 utils. If missing, use local helpers.
try:
    from bot.utils.math_tools import log_returns as _mt_log_returns  # type: ignore
except Exception:  # pragma: no cover
    _mt_log_returns = None


# ---------------------------------------------------------------------------
# Local helpers (used if utils.math_tools not present)

def _log_returns_local(prices: pd.Series) -> pd.Series:
    prices = pd.Series(prices).astype(float)
    lr = np.log(prices).diff()
    return lr.dropna()


def _annualize_vol(std_step: float, steps_per_year: float) -> float:
    return float(std_step * math.sqrt(steps_per_year))


def _deannualize_vol(std_annual: float, steps_per_year: float) -> float:
    return float(std_annual / math.sqrt(steps_per_year))


# ---------------------------------------------------------------------------
# Public utilities

def dt_from_minutes_fx(minutes_per_bar: int | float) -> float:
    """Return dt (in years) for FX/Metals (24/5 approximation) given bar length in minutes.

    We approximate a trading year as 365 days * 24 hours. This is conservative for FX/metals
    which are near 24/5. If you prefer 252 trading days * 24 hours, adjust below.
    """
    minutes_per_year = 365.0 * 24.0 * 60.0
    return float(minutes_per_bar) / minutes_per_year


def steps_per_year_from_minutes(minutes_per_bar: int | float) -> float:
    minutes_per_year = 365.0 * 24.0 * 60.0
    return minutes_per_year / float(minutes_per_bar)


@dataclass
class Calibration:
    mu_annual: float
    sigma_annual: float
    steps_per_year: float

    @property
    def mu_step(self) -> float:
        return self.mu_annual / self.steps_per_year

    @property
    def sigma_step(self) -> float:
        return _deannualize_vol(self.sigma_annual, self.steps_per_year)


class VolEstimator:
    """Volatility & drift estimators.

    Methods provide:
      - realized volatility from returns
      - EWMA volatility (RiskMetrics style)
      - drift estimation from mean log-returns
    """

    @staticmethod
    def log_returns(series: pd.Series) -> pd.Series:
        if _mt_log_returns is not None:
            try:
                return _mt_log_returns(series)
            except Exception:
                pass
        return _log_returns_local(series)

    @staticmethod
    def realized_vol(returns: pd.Series, steps_per_year: float) -> float:
        r = pd.Series(returns).dropna().astype(float)
        if len(r) < 2:
            return 0.0
        std_step = float(r.std(ddof=1))
        return _annualize_vol(std_step, steps_per_year)

    @staticmethod
    def ewma_vol(returns: pd.Series, steps_per_year: float, lam: float = 0.94) -> float:
        """EWMA annualized volatility (RiskMetrics).

        lam: decay factor in (0,1). Higher → slower decay. Default 0.94.
        """
        r = pd.Series(returns).dropna().astype(float)
        if len(r) < 2:
            return 0.0
        # Initialize with sample variance
        var = float(np.var(r.values, ddof=1))
        for x in r.values:
            var = lam * var + (1 - lam) * (x ** 2)
        std_step = math.sqrt(var)
        return _annualize_vol(std_step, steps_per_year)

    @staticmethod
    def drift(returns: pd.Series, steps_per_year: float) -> float:
        r = pd.Series(returns).dropna().astype(float)
        if len(r) == 0:
            return 0.0
        # Mean of log-returns per step → annualized drift (approx mu)
        mean_step = float(r.mean())
        return mean_step * steps_per_year

    @staticmethod
    def calibrate_from_prices(
        prices: pd.Series,
        minutes_per_bar: int | float,
        use_ewma: bool = True,
        ewma_lambda: float = 0.94,
    ) -> Calibration:
        prices = pd.Series(prices).dropna().astype(float)
        if len(prices) < 20:
            raise ValueError("Need at least 20 price points to calibrate.")

        steps_per_year = steps_per_year_from_minutes(minutes_per_bar)
        rets = VolEstimator.log_returns(prices)
        mu_annual = VolEstimator.drift(rets, steps_per_year)
        if use_ewma:
            sigma_annual = VolEstimator.ewma_vol(rets, steps_per_year, lam=ewma_lambda)
        else:
            sigma_annual = VolEstimator.realized_vol(rets, steps_per_year)

        return Calibration(mu_annual=mu_annual, sigma_annual=sigma_annual, steps_per_year=steps_per_year)


# ---------------------------------------------------------------------------
# Brownian Motion

class BrownianMotion:
    """Discrete Brownian Motion (Wiener process) generator.

    W_{t+dt} = W_t + sqrt(dt) * N(0,1)

    Use cases:
      - Drive GBM
      - Create noise for stress tests
    """

    def __init__(self, seed: Optional[int] = None):
        self._rng = np.random.default_rng(seed)

    def sample(self, n_steps: int, dt: float) -> np.ndarray:
        if n_steps <= 0:
            return np.empty(0, dtype=float)
        increments = self._rng.normal(loc=0.0, scale=math.sqrt(dt), size=int(n_steps))
        return increments.cumsum()

    def steps(self, n_steps: int, dt: float) -> np.ndarray:
        """Independent N(0, dt) increments without cumulative sum."""
        if n_steps <= 0:
            return np.empty(0, dtype=float)
        return self._rng.normal(loc=0.0, scale=math.sqrt(dt), size=int(n_steps))


# ---------------------------------------------------------------------------
# Geometric Brownian Motion (GBM)

class GBMSimulator:
    """Geometric Brownian Motion simulator for prices.

    dS_t = mu * S_t * dt + sigma * S_t * dW_t
    Discrete solution for one step:
        S_{t+dt} = S_t * exp((mu - 0.5*sigma^2)*dt + sigma*sqrt(dt)*Z), Z~N(0,1)

    Notes
    -----
    - `mu` and `sigma` are ANNUALIZED parameters. We convert internally to step units using dt.
    - Supports multi-path simulation for scenario analysis.
    - Provides `sample_next_step` for live tick/next-bar prediction.
    """

    def __init__(
        self,
        mu_annual: float,
        sigma_annual: float,
        dt: float,
        seed: Optional[int] = None,
    ):
        if sigma_annual < 0:
            raise ValueError("sigma_annual must be non-negative")
        if dt <= 0:
            raise ValueError("dt must be positive (years per step)")

        self.mu_annual = float(mu_annual)
        self.sigma_annual = float(sigma_annual)
        self.dt = float(dt)
        self._rng = np.random.default_rng(seed)

    # --------- Properties in step units
    @property
    def mu_step(self) -> float:
        return self.mu_annual * self.dt

    @property
    def sigma_step(self) -> float:
        return self.sigma_annual * math.sqrt(self.dt)

    # --------- Core methods
    def sample_next_step(self, s_t: float) -> float:
        """Draw one GBM step from price s_t → s_{t+dt}."""
        z = self._rng.normal(0.0, 1.0)
        drift = (self.mu_annual - 0.5 * (self.sigma_annual ** 2)) * self.dt
        diffusion = self.sigma_annual * math.sqrt(self.dt) * z
        return float(s_t * math.exp(drift + diffusion))

    def simulate_path(self, s0: float, n_steps: int) -> np.ndarray:
        if n_steps <= 0:
            return np.array([float(s0)])
        z = self._rng.normal(0.0, 1.0, size=int(n_steps))
        drift = (self.mu_annual - 0.5 * (self.sigma_annual ** 2)) * self.dt
        diffusion = self.sigma_annual * math.sqrt(self.dt) * z
        log_increments = drift + diffusion
        log_path = np.log(s0) + np.cumsum(log_increments)
        prices = np.exp(log_path)
        return np.concatenate([[float(s0)], prices])

    def simulate_paths(self, s0: float, n_steps: int, n_paths: int) -> np.ndarray:
        """Return array shape (n_paths, n_steps+1)."""
        if n_steps <= 0 or n_paths <= 0:
            return np.full((max(1, int(n_paths)), max(1, int(n_steps)) + 1), float(s0))
        z = self._rng.normal(0.0, 1.0, size=(int(n_paths), int(n_steps)))
        drift = (self.mu_annual - 0.5 * (self.sigma_annual ** 2)) * self.dt
        diffusion = self.sigma_annual * math.sqrt(self.dt) * z
        log_increments = drift + diffusion
        log_paths = np.log(s0) + np.cumsum(log_increments, axis=1)
        prices = np.exp(log_paths)
        s0_col = np.full((int(n_paths), 1), float(s0))
        return np.concatenate([s0_col, prices], axis=1)

    # --------- Convenience
    def to_dataframe(
        self,
        s0: float,
        n_steps: int,
        index: Optional[pd.DatetimeIndex] = None,
        n_paths: int = 1,
    ) -> pd.DataFrame:
        """Simulate and return a DataFrame for easy plotting/inspection."""
        arr = self.simulate_paths(s0=s0, n_steps=n_steps, n_paths=n_paths)
        cols = [f"path_{i+1}" for i in range(arr.shape[0])]
        df = pd.DataFrame(arr.T, columns=cols)
        if index is not None and len(index) == len(df):
            df.index = index
        return df

    # --------- Static helpers
    @staticmethod
    def from_prices(
        prices: pd.Series,
        minutes_per_bar: int | float,
        use_ewma: bool = True,
        ewma_lambda: float = 0.94,
        seed: Optional[int] = None,
    ) -> "GBMSimulator":
        """Calibrate mu/sigma from a price series and build a GBMSimulator."""
        calib = VolEstimator.calibrate_from_prices(
            prices=prices,
            minutes_per_bar=minutes_per_bar,
            use_ewma=use_ewma,
            ewma_lambda=ewma_lambda,
        )
        dt = dt_from_minutes_fx(minutes_per_bar)
        return GBMSimulator(
            mu_annual=calib.mu_annual,
            sigma_annual=calib.sigma_annual,
            dt=dt,
            seed=seed,
        )


# ---------------------------------------------------------------------------
# Quick self-test (optional). Run directly: `python -m bot.models.stochastic`

if __name__ == "__main__":  # pragma: no cover
    # Synthetic sanity check
    rng = np.random.default_rng(7)
    close = pd.Series(2000 + np.cumsum(rng.normal(0, 2, size=500)))  # fake XAUUSD-ish

    minutes = 5
    sim = GBMSimulator.from_prices(close, minutes_per_bar=minutes, use_ewma=True)
    print("Calibrated mu_annual=", round(sim.mu_annual, 6), "sigma_annual=", round(sim.sigma_annual, 6))

    df_paths = sim.to_dataframe(s0=float(close.iloc[-1]), n_steps=120, n_paths=5)
    print(df_paths.head())
