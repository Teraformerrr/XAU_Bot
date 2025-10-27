import json
import numpy as np
import pandas as pd
from datetime import datetime
from loguru import logger
from pathlib import Path


class PortfolioMetrics:
    """
    Computes advanced performance metrics from logged trades in portfolio.json.
    """

    def __init__(self, portfolio_file: str = "portfolio.json"):
        self.path = Path(portfolio_file)
        self.trades = []
        self.portfolio = {}
        self._load()

    def _load(self):
        if not self.path.exists():
            logger.warning("⚠️ No portfolio file found — metrics will be empty.")
            return
        with open(self.path, "r") as f:
            data = json.load(f)
        self.trades = data.get("trades", [])
        self.portfolio = data.get("portfolio", {})
        logger.info(f"📊 Loaded {len(self.trades)} trades for metrics calculation.")

    # ----------------------------------------------------
    # Core Calculations
    # ----------------------------------------------------
    def compute_basic_metrics(self):
        """Compute win rate, average PnL, expectancy, and equity growth."""
        if not self.trades:
            return {}

        df = pd.DataFrame(self.trades)
        pnl = df["pnl"].astype(float)
        wins = pnl[pnl > 0]
        losses = pnl[pnl <= 0]

        win_rate = len(wins) / len(pnl) if len(pnl) > 0 else 0
        avg_win = wins.mean() if not wins.empty else 0
        avg_loss = losses.mean() if not losses.empty else 0
        expectancy = (win_rate * avg_win) + ((1 - win_rate) * avg_loss)

        equity_curve = pnl.cumsum()
        total_return = pnl.sum()
        max_drawdown = self._max_drawdown(equity_curve)

        return {
            "total_trades": len(pnl),
            "win_rate": round(win_rate * 100, 2),
            "avg_win": round(avg_win, 2),
            "avg_loss": round(avg_loss, 2),
            "expectancy": round(expectancy, 2),
            "total_return": round(total_return, 2),
            "max_drawdown": round(max_drawdown, 2)
        }

    def compute_risk_metrics(self, risk_free_rate=0.02):
        """Compute Sharpe, Sortino, Calmar ratios."""
        if not self.trades:
            return {}

        df = pd.DataFrame(self.trades)
        returns = df["pnl"].astype(float)
        daily_returns = returns / (self.portfolio.get("equity", 1) or 1)
        mean_ret = np.mean(daily_returns)
        std_ret = np.std(daily_returns)
        downside_std = np.std(daily_returns[daily_returns < 0])

        sharpe = (mean_ret - risk_free_rate / 252) / (std_ret + 1e-9)
        sortino = (mean_ret - risk_free_rate / 252) / (downside_std + 1e-9)
        max_drawdown = self._max_drawdown(returns.cumsum())
        calmar = mean_ret / (abs(max_drawdown) + 1e-9)

        return {
            "sharpe": round(sharpe, 3),
            "sortino": round(sortino, 3),
            "calmar": round(calmar, 3)
        }

    def compute_consistency_metrics(self):
        """Evaluate consistency and volatility of results."""
        if not self.trades:
            return {}

        df = pd.DataFrame(self.trades)
        pnl = df["pnl"].astype(float)
        rolling_mean = pnl.rolling(window=5).mean()
        rolling_std = pnl.rolling(window=5).std()

        consistency = np.mean(np.abs(rolling_mean) / (rolling_std + 1e-9))
        volatility = np.std(pnl)

        return {
            "consistency_score": round(consistency, 3),
            "volatility": round(volatility, 3)
        }

    def _max_drawdown(self, equity_curve):
        """Helper to calculate maximum drawdown."""
        cumulative_max = np.maximum.accumulate(equity_curve)
        drawdown = equity_curve - cumulative_max
        return np.min(drawdown)

    def summary(self):
        """Full portfolio analytics summary."""
        basic = self.compute_basic_metrics()
        risk = self.compute_risk_metrics()
        consistency = self.compute_consistency_metrics()
        merged = {**basic, **risk, **consistency}
        merged["timestamp"] = datetime.utcnow().isoformat()
        logger.info(f"✅ Portfolio metrics computed at {merged['timestamp']}")
        return merged


if __name__ == "__main__":
    pm = PortfolioMetrics("portfolio.json")
    summary = pm.summary()
    print("\n--- PORTFOLIO METRICS SUMMARY ---")
    for k, v in summary.items():
        print(f"{k:20s}: {v}")
