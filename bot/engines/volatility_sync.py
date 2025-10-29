"""
Volatility Synchronizer
──────────────────────────────
Keeps last known volatility value synced across modules.
"""

import json, os, time
from datetime import datetime
from pathlib import Path

class VolatilitySynchronizer:
    def __init__(self, path="data/vol_sync.json", expiry=300):
        self.path = path
        self.expiry = expiry
        Path(os.path.dirname(path)).mkdir(parents=True, exist_ok=True)

    def update(self, symbol, volatility):
        data = {
            "timestamp": datetime.utcnow().isoformat(),
            "symbol": symbol,
            "volatility": float(volatility),
        }
        with open(self.path, "w") as f:
            json.dump(data, f)
        return data

    def get(self, symbol):
        if not os.path.exists(self.path):
            return 0.1
        try:
            with open(self.path, "r") as f:
                data = json.load(f)
            age = time.time() - datetime.fromisoformat(data["timestamp"]).timestamp()
            if age > self.expiry:
                print(f"⚠️ VolSync expired ({age:.1f}s old)")
                return 0.1
            return float(data.get("volatility", 0.1))
        except Exception:
            return 0.1
