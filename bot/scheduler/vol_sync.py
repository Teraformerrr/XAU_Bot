# bot/scheduler/vol_sync.py
import json, os, time
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class VolatilitySynchronizer:
    """Keeps volatility consistent across modules (Router, Scheduler, DRG, Feedback)."""

    def __init__(self, state_path="vol_state.json", expiry_sec=120):
        self.state_path = state_path
        self.expiry_sec = expiry_sec

    def update(self, symbol: str, volatility: float):
        """Update global volatility state."""
        data = {
            "timestamp": datetime.utcnow().isoformat(),
            "symbol": symbol,
            "volatility": volatility
        }
        with open(self.state_path, "w") as f:
            json.dump(data, f, indent=2)
        logger.info(f"🌐 VolSync updated | {symbol} | vol={volatility:.4f}")

    def read(self):
        """Read current volatility state, validate freshness."""
        if not os.path.exists(self.state_path):
            return None
        with open(self.state_path, "r") as f:
            data = json.load(f)
        ts = datetime.fromisoformat(data["timestamp"])
        age = (datetime.utcnow() - ts).total_seconds()
        if age > self.expiry_sec:
            logger.warning(f"⚠️ VolSync expired ({age:.1f}s old)")
            return None
        return data

    def get_volatility(self, default=0.1):
        """Return latest volatility (or default if expired/unavailable)."""
        data = self.read()
        if data:
            return data.get("volatility", default)
        return default
