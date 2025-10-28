import json
import numpy as np
import logging
from datetime import datetime
from bot.utils.logger import configure_logger

logger = configure_logger("VolatilityTuner", "reports/tuning_log.jsonl")

class VolatilityAwareTuner:
    """
    Adjusts trading thresholds based on recent volatility (ATR, stddev).
    Expands thresholds in high volatility to avoid false signals.
    Contracts them in low volatility to stay responsive.
    """

    def __init__(self, base_buy_th=0.555, base_sell_th=0.445, vol_window=50, k_vol=1.5):
        self.base_buy_th = base_buy_th
        self.base_sell_th = base_sell_th
        self.vol_window = vol_window
        self.k_vol = k_vol
        self.history = []

    def update(self, confidence: float, volatility: float):
        """Record recent confidence/volatility observations."""
        self.history.append((confidence, volatility))
        if len(self.history) > self.vol_window:
            self.history.pop(0)

    def compute_volatility_factor(self):
        """Compute volatility factor from recent volatility history."""
        vols = [v for _, v in self.history]
        if len(vols) < 5:
            return 1.0  # Not enough data yet
        mean_vol = np.mean(vols)
        std_vol = np.std(vols)
        latest_vol = vols[-1]
        factor = 1.0 + self.k_vol * (latest_vol - mean_vol) / (std_vol + 1e-8)
        return np.clip(factor, 0.8, 1.4)

    def tuned_thresholds(self):
        """Return dynamically tuned thresholds based on volatility factor."""
        f = self.compute_volatility_factor()
        buy_th = min(0.7, self.base_buy_th * f)
        sell_th = max(0.3, self.base_sell_th * (2 - f))
        neutral_band = (buy_th - sell_th) / 2
        logger.info(json.dumps({
            "timestamp": datetime.utcnow().isoformat(),
            "volatility_factor": round(f, 4),
            "buy_th": round(buy_th, 4),
            "sell_th": round(sell_th, 4),
            "neutral_band": round(neutral_band, 4)
        }))
        return buy_th, sell_th, neutral_band
