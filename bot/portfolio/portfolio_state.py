import os
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class PortfolioState:
    """
    Handles loading and saving of the current portfolio.json state.
    Provides equity, realized PnL, and trade count for consistency checks.
    """

    def __init__(self, state_path: str = "portfolio.json"):
        self.state_path = state_path

    def load(self) -> dict:
        """
        Loads portfolio.json and returns the last known portfolio state.
        Creates a default state if none exists.
        """
        if not os.path.exists(self.state_path):
            logger.info("🆕 Creating new portfolio.json (no existing state found).")
            default_state = {
                "equity": 100000.0,
                "realized_pnl": 0.0,
                "unrealized_pnl": 0.0,
                "win_trades": 0,
                "loss_trades": 0,
                "total_trades": 0,
                "last_update": datetime.utcnow().isoformat()
            }
            self._save(default_state)
            return default_state

        try:
            with open(self.state_path, "r") as f:
                data = json.load(f)
                portfolio = data.get("portfolio", data)

                # 🧠 Fix: If equity is 0 or missing, reset to baseline
                if portfolio.get("equity", 0) <= 0:
                    portfolio["equity"] = 100000.0

                return portfolio
        except Exception as e:
            logger.error(f"⚠️ Failed to load portfolio.json: {e}")
            return {}

    def save(self, portfolio: dict):
        """
        Saves updated portfolio state to portfolio.json.
        """
        try:
            with open(self.state_path, "r") as f:
                data = json.load(f)
        except Exception:
            data = {"portfolio": portfolio, "trades": []}

        data["portfolio"] = portfolio

        with open(self.state_path, "w") as f:
            json.dump(data, f, indent=2)

        logger.info("💾 Portfolio state saved successfully.")
        return True

    def _save(self, portfolio: dict):
        """
        Internal helper for initial save during first run.
        """
        os.makedirs(os.path.dirname(self.state_path) or ".", exist_ok=True)
        with open(self.state_path, "w") as f:
            json.dump({"portfolio": portfolio, "trades": []}, f, indent=2)
