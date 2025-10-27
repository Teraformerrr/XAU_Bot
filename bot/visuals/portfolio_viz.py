# bot/visuals/portfolio_viz.py
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")

class PortfolioVisualizer:
    def __init__(self, trade_log_path="data/trade_log.csv", output_dir="reports"):
        self.trade_log_path = Path(trade_log_path)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.df = None

    def load_trades(self):
        if not self.trade_log_path.exists():
            logging.warning(f"No trade log found at {self.trade_log_path}")
            return None

        self.df = pd.read_csv(self.trade_log_path, parse_dates=["timestamp"])
        self.df.sort_values("timestamp", inplace=True)
        logging.info(f"Loaded {len(self.df)} trades for visualization.")
        return self.df

    def plot_equity_curve(self):
        if self.df is None:
            self.load_trades()
        if "pnl" not in self.df.columns:
            logging.warning("No PnL column found. Cannot plot equity curve.")
            return

        self.df["equity_curve"] = self.df["pnl"].cumsum()
        plt.figure(figsize=(10, 5))
        plt.plot(self.df["timestamp"], self.df["equity_curve"], label="Equity Curve", linewidth=2)
        plt.xlabel("Date")
        plt.ylabel("Cumulative PnL (USD)")
        plt.title("Portfolio Equity Curve")
        plt.legend()
        plt.grid(True)
        plt.tight_layout()
        output_path = self.output_dir / "equity_curve.png"
        plt.savefig(output_path)
        plt.close()
        logging.info(f"✅ Equity curve saved → {output_path}")

    def plot_win_loss_distribution(self):
        if self.df is None:
            self.load_trades()

        plt.figure(figsize=(6, 5))
        sns.histplot(self.df["pnl"], bins=20, kde=True, color="gold")
        plt.axvline(0, color="red", linestyle="--")
        plt.title("Win/Loss Distribution")
        plt.xlabel("PnL (USD)")
        plt.ylabel("Frequency")
        plt.tight_layout()
        output_path = self.output_dir / "win_loss_distribution.png"
        plt.savefig(output_path)
        plt.close()
        logging.info(f"✅ Win/Loss distribution saved → {output_path}")

    def plot_monthly_performance(self):
        if self.df is None:
            self.load_trades()

        self.df["month"] = self.df["timestamp"].dt.to_period("M")
        monthly_pnl = self.df.groupby("month")["pnl"].sum().to_timestamp()

        plt.figure(figsize=(10, 5))
        sns.barplot(x=monthly_pnl.index, y=monthly_pnl.values, color="skyblue")
        plt.xticks(rotation=45)
        plt.title("Monthly Performance")
        plt.xlabel("Month")
        plt.ylabel("Total PnL (USD)")
        plt.tight_layout()
        output_path = self.output_dir / "monthly_performance.png"
        plt.savefig(output_path)
        plt.close()
        logging.info(f"✅ Monthly performance saved → {output_path}")

    def plot_drawdown(self):
        if self.df is None:
            self.load_trades()

        equity = self.df["pnl"].cumsum()
        rolling_max = equity.cummax()
        drawdown = equity - rolling_max

        plt.figure(figsize=(10, 5))
        plt.fill_between(self.df["timestamp"], drawdown, color="red", alpha=0.3)
        plt.title("Drawdown Over Time")
        plt.xlabel("Date")
        plt.ylabel("Drawdown (USD)")
        plt.tight_layout()
        output_path = self.output_dir / "drawdown.png"
        plt.savefig(output_path)
        plt.close()
        logging.info(f"✅ Drawdown chart saved → {output_path}")

    def generate_all(self):
        logging.info("📊 Generating all portfolio visualizations...")
        self.load_trades()
        self.plot_equity_curve()
        self.plot_win_loss_distribution()
        self.plot_monthly_performance()
        self.plot_drawdown()
        logging.info("✅ All visualizations generated successfully.")
