import json
import numpy as np
from datetime import datetime, timedelta
from loguru import logger

class BayesianMemory:
    """
    Tracks performance and drift of each Bayesian signal component.
    Provides adaptive priors and volatility-aware decay.
    """

    def __init__(self, state_file="bayes_state.json", decay=0.995, drift_threshold=0.15):
        self.state_file = state_file
        self.decay = decay
        self.drift_threshold = drift_threshold
        self.state = self._load_state()

    def _load_state(self):
        try:
            with open(self.state_file, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning("⚠️ No bayes_state.json found — initializing new memory.")
            return {}

    def _save_state(self):
        with open(self.state_file, "w") as f:
            json.dump(self.state, f, indent=2)

    def update_memory(self, symbol, signal_name, outcome):
        """
        outcome = 1 (correct signal), 0 (incorrect)
        """
        node = self.state.get(symbol, {}).get("signals", {}).get(signal_name)
        if not node:
            return

        a, b = node["a"], node["b"]
        a = self.decay * a + outcome
        b = self.decay * b + (1 - outcome)

        node["a"], node["b"] = a, b
        self._save_state()

    def detect_drift(self, symbol, recent_vols):
        """
        Compare rolling volatility vs long-term mean to detect drift.
        """
        if len(recent_vols) < 20:
            return False

        current_vol = np.mean(recent_vols[-10:])
        long_vol = np.mean(recent_vols)
        drift = abs(current_vol - long_vol) / long_vol if long_vol > 0 else 0

        if drift > self.drift_threshold:
            logger.info(f"⚠️ Drift detected in {symbol}: vol shift {drift:.2f}")
            return True
        return False

    def apply_drift_correction(self, symbol):
        """
        When drift occurs, slightly flatten priors (forget old bias).
        """
        if symbol not in self.state:
            return
        for sig in self.state[symbol]["signals"].values():
            sig["a"] = 50 + (sig["a"] - 50) * 0.5
            sig["b"] = 50 + (sig["b"] - 50) * 0.5
        self._save_state()
        logger.info(f"🔄 Priors flattened for {symbol} due to regime drift.")
