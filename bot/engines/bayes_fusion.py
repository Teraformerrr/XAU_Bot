import json
import os
import logging
from typing import Dict, Tuple

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")

# ──────────────────────────────────────────────────────────────────────────────
# Bayesian Fusion — now includes LSTM confidence as a first-class component
# Components expected in `components` dict (probabilities 0..1):
#   - kf_trend, ou_revert, stoch_momo, kf_slope, ou_zscore, lstm
# Any missing component will be skipped gracefully.
# ──────────────────────────────────────────────────────────────────────────────

DEFAULT_WEIGHTS = {
    "trend":  {"kf_trend": 0.30, "kf_slope": 0.25, "stoch_momo": 0.15, "ou_revert": 0.10, "ou_zscore": 0.05, "lstm": 0.15},
    "range":  {"kf_trend": 0.15, "kf_slope": 0.15, "stoch_momo": 0.15, "ou_revert": 0.25, "ou_zscore": 0.15, "lstm": 0.15},
    "chop":   {"kf_trend": 0.20, "kf_slope": 0.15, "stoch_momo": 0.20, "ou_revert": 0.20, "ou_zscore": 0.10, "lstm": 0.15},
}

class BayesianFusion:
    def __init__(self, state_path: str = "bayes_state.json", weights: Dict[str, Dict[str, float]] = None):
        self.state_path = state_path
        self.weights = weights or DEFAULT_WEIGHTS
        self._ensure_state()

    # Persist priors/posteriors if you use them; kept compatible with previous steps.
    def _ensure_state(self):
        if not os.path.exists(self.state_path):
            os.makedirs(os.path.dirname(self.state_path), exist_ok=True)
            with open(self.state_path, "w") as f:
                json.dump({"XAUUSD": {"prior": {"a": 50.0, "b": 50.0}, "signals": {}}}, f, indent=2)

    def fused_decision(
        self,
        components: Dict[str, float],
        regime: str = "trend",
        vol: float = 0.0,
        buy_sell_band: Tuple[float, float] = (0.555, 0.445)
    ) -> Dict:
        """
        components: dict of {name: probability in [0,1]}
        regime: 'trend' | 'range' | 'chop'
        vol:    normalized vol (0..1) used for adaptive widening/narrowing
        buy_sell_band: center thresholds before adaptive adjustments
        """
        # 1) Choose weights by regime
        regime_key = regime if regime in self.weights else "trend"
        regime_w = self.weights[regime_key]

        # 2) Keep only available components
        active = {k: v for k, v in components.items() if k in regime_w and v is not None}
        if not active:
            return {"combined_conf": 0.5, "action": "HOLD", "weights": {}, "components": {}, "regime": regime, "vol": vol}

        # 3) Normalize weights over active components
        total_w = sum(regime_w[k] for k in active.keys())
        norm_w = {k: (regime_w[k] / total_w) for k in active.keys()} if total_w > 0 else {k: 1/len(active) for k in active.keys()}

        # 4) Weighted probability
        combined = sum(active[k] * norm_w[k] for k in active.keys())

        # 5) Adaptive thresholds (widen in high vol, narrow in low vol)
        base_buy, base_sell = buy_sell_band
        # vol in [0,1]: widen up to ±0.05 at extreme vol
        widen = 0.05 * vol
        buy_th = min(0.5 + (base_buy - 0.5) + widen, 0.80)  # cap extremes
        sell_th = max(0.5 - (0.5 - base_sell) - widen, 0.20)

        if combined > buy_th:
            action = "BUY"
        elif combined < sell_th:
            action = "SELL"
        else:
            action = "HOLD"

        logging.info(f"🔗 Fusion: regime={regime} vol={vol:.2f} → prob={combined:.4f} | band=({sell_th:.3f},{buy_th:.3f}) | action={action}")

        return {
            "combined_conf": round(combined, 4),
            "action": action,
            "weights": norm_w,
            "components": active,
            "regime": regime_key,
            "vol": vol,
            "thresholds": (round(buy_th, 3), round(sell_th, 3))
        }

    def decision(self):
        """
        Compatibility wrapper so external modules can call BayesianFusion.decision()
        without passing explicit components.
        """
        try:
            # If your model already builds its components internally, use that.
            if hasattr(self, "components") and self.components:
                return self.fused_decision(self.components)
            # Otherwise call with empty dict (will return neutral output)
            return self.fused_decision({})
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"BayesianFusion.decision() fallback error: {e}")
            return {
                "combined_conf": 0.5,
                "vol": 0.05,
                "action": "HOLD"
            }


# Standalone demo (optional)
if __name__ == "__main__":
    demo = BayesianFusion()
    comps = {
        "kf_trend": 0.52,
        "kf_slope": 0.51,
        "stoch_momo": 0.49,
        "ou_revert": 0.47,
        "ou_zscore": 0.50,
        "lstm": 0.61,  # ← LSTM now included
    }
    out = demo.fused_decision(comps, regime="trend", vol=0.10)
    print(out)
