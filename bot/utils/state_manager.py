import json
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

class PortfolioState:
    """
    Handles saving and loading of portfolio state.
    Keeps track of equity, realized/unrealized PnL, trade counts, etc.
    """

    def __init__(self, path: str = "portfolio_state.json"):
        self.path = Path(path)
        self.state = self._load_state()

    # ------------------------------------------------------------------
    def _load_state(self):
        """Load existing state from file or create a new default one."""
        if self.path.exists():
            try:
                with open(self.path, "r") as f:
                    data = json.load(f)
                logger.debug("📂 Portfolio state loaded from %s", self.path)
                return data
            except Exception as e:
                logger.warning("⚠️ Could not read portfolio_state.json → %s", e)

        # Default state
        default_state = {
            "equity": 100000.0,
            "realized_pnl": 0.0,
            "unrealized_pnl": 0.0,
            "win_trades": 0,
            "loss_trades": 0,
            "total_trades": 0,
            "timestamp": datetime.utcnow().isoformat(),
        }
        self._save_state(default_state)
        return default_state

    # ------------------------------------------------------------------
    def _save_state(self, data: dict):
        """Write state to JSON file."""
        try:
            with open(self.path, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error("❌ Failed to save portfolio state: %s", e)

    # ------------------------------------------------------------------
    def update_from_trade(self, trade: dict):
        """
        Update portfolio metrics based on trade result.
        """
        pnl = trade.get("pnl", 0.0)
        equity = self.state.get("equity", 100000.0) + pnl

        # Win/loss counters
        if pnl > 0:
            self.state["win_trades"] += 1
        elif pnl < 0:
            self.state["loss_trades"] += 1

        self.state["total_trades"] += 1
        self.state["realized_pnl"] += pnl
        self.state["equity"] = equity
        self.state["timestamp"] = datetime.utcnow().isoformat()

        self._save_state(self.state)
        logger.info("💾 Portfolio updated | Equity=%.2f | PnL=%.2f", equity, pnl)

    # ------------------------------------------------------------------
    def read(self):
        """Return current portfolio dictionary."""
        return self.state
