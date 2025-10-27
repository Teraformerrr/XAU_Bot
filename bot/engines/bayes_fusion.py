# D:\XAU_Bot\bot\engines\bayes_fusion.py
from __future__ import annotations
import json
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List, Optional
from loguru import logger
import numpy as np
import pandas as pd

from bot.engines.dynamic_weights import DynamicWeighting
from bot.utils.regime import rolling_volatility, detect_regime

@dataclass
class SignalPosterior:
    a: float
    b: float

    @property
    def mean(self) -> float:
        # posterior mean of Beta(a,b)
        denom = self.a + self.b
        return 0.5 if denom <= 0 else self.a / denom

class BayesianFusion:
    """
    Adaptive Bayesian Fusion with dynamic, performance- and regime-aware weights.
    State 1 (existing): bayes_state.json -> Beta posteriors per signal
    State 2 (new)    : weights_state.json -> EWMA accuracy & variance per signal
    """
    def __init__(self, bayes_state_path: str = "bayes_state.json", weights_state_path: str = "weights_state.json"):
        self.path = Path(bayes_state_path)
        self.state = self._load_json(self.path)
        self.dw = DynamicWeighting(weights_state_path)
        # Wire-up your known signal names here (must match your bayes_state keys)
        self.signal_order = ["kf_trend", "ou_revert", "stoch_momo", "kf_slope", "ou_zscore"]

    @staticmethod
    def _load_json(p: Path) -> dict:
        if not p.exists():
            raise FileNotFoundError(f"{p} not found. Run Step 4/5 to initialize bayes_state.json.")
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception as e:
            raise RuntimeError(f"Failed to read {p}: {e}")

    def _get_posteriors(self, symbol: str) -> Dict[str, SignalPosterior]:
        node = self.state.get(symbol, {})
        sigs = node.get("signals", {})
        post: Dict[str, SignalPosterior] = {}
        for name in self.signal_order:
            ab = sigs.get(name, {"a": 50.0, "b": 50.0})
            post[name] = SignalPosterior(a=float(ab.get("a", 50.0)), b=float(ab.get("b", 50.0)))
        return post

    def _fetch_recent_close(self, symbol: str, bars: int = 200) -> pd.Series:
        """
        Lightweight placeholder. Replace with your real OHLC fetcher.
        This function must return a pandas Series of close prices.
        """
        # In your integration: call your MT5/OHLC store.
        # For now create a synthetic flat series to avoid breaking.
        idx = pd.RangeIndex(0, bars)
        return pd.Series(np.linspace(2400, 2410, bars), index=idx, name="close")

    def fused_decision(
        self,
        symbol: str,
        kf_slope_value: Optional[float] = None,
        close_series: Optional[pd.Series] = None,
        min_trade_conf: float = 0.56
    ) -> Dict[str, float | str]:
        """
        Returns a dict with:
          - combined_conf: float in [0,1]
          - action: 'BUY' | 'SELL' | 'HOLD'
          - weights: per-signal weights used this tick
          - components: per-signal posterior means
        """
        post = self._get_posteriors(symbol)
        components = {k: v.mean for k, v in post.items()}

        # Get data for regime/vol
        close = close_series if close_series is not None else self._fetch_recent_close(symbol)
        vol = rolling_volatility(close, window=50)   # ~0 to ~0.05 typical daily % range
        regime = detect_regime(close, kf_slope_value)

        # Dynamic weights
        w = self.dw.compute(symbol, self.signal_order, regime=regime, vol=vol)

        # Weighted mean around 0.5 baseline
        # Convert each posterior mean pi to logit domain for smoother blend, then back
        def safe_logit(p: float) -> float:
            eps = 1e-6
            p = min(1 - eps, max(eps, p))
            return np.log(p / (1 - p))

        logits = np.array([safe_logit(components[s]) for s in self.signal_order], dtype=float)
        weights = np.array([w[s] for s in self.signal_order], dtype=float)
        fused_logit = float(np.sum(weights * logits))
        fused_p = 1.0 / (1.0 + np.exp(-fused_logit))

        # Map to action with a neutral band
        if fused_p >= min_trade_conf:
            action = "BUY"
        elif fused_p <= (1.0 - min_trade_conf):
            action = "SELL"
        else:
            action = "HOLD"

        logger.info(f"{symbol}: conf={fused_p:.4f} | regime={regime} | vol={vol:.4f} | action={action}")
        return {
            "combined_conf": round(fused_p, 4),
            "action": action,
            "weights": {k: round(w[k], 3) for k in self.signal_order},
            "components": {k: round(components[k], 4) for k in self.signal_order},
            "regime": regime,
            "vol": round(vol, 5)
        }

    # === Public hook to log outcomes (call this from your strategy once you know result) ===
    def register_signal_outcome(self, symbol: str, signal_name: str, correct: bool) -> None:
        self.dw.register_outcome(symbol, signal_name, correct)
