import numpy as np
import pandas as pd

# Labels: 1=BUY, -1=SELL, 0=HOLD
LABELS_MAP = {"SELL": -1, "HOLD": 0, "BUY": 1}

class Labeler:
    def __init__(self, horizon_bars: int, threshold_pct: float):
        self.h = int(horizon_bars)
        self.t = float(threshold_pct) / 100.0  # convert % to fraction

    def make_labels(self, df: pd.DataFrame) -> np.ndarray:
        if "close" not in df.columns:
            raise ValueError("close column required for labeling")

        close = df["close"].astype(float).values
        future = np.roll(close, -self.h)
        # Last h rows don't have future; mark as NaN to drop later
        future[-self.h:] = np.nan

        ret = (future - close) / close
        labels = np.zeros_like(ret, dtype=int)

        labels[ret >= self.t] = LABELS_MAP["BUY"]
        labels[ret <= -self.t] = LABELS_MAP["SELL"]
        # HOLD stays 0

        return labels
