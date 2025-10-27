# D:\XAU_Bot\bot\engines\dynamic_weights.py
from __future__ import annotations
import json, time
from pathlib import Path
from math import exp
from typing import Dict, List

def _safe_load_json(p: Path) -> dict:
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}

def _safe_dump_json(p: Path, obj: dict) -> None:
    p.write_text(json.dumps(obj, indent=2), encoding="utf-8")

class DynamicWeighting:
    """
    Maintains per-signal, per-symbol weights that adapt to:
    - recent EWMA accuracy (hit-rate proxy)
    - stability (variance penalty)
    - regime alignment (trend vs range)
    All weights are softmax-normalized.
    """
    def __init__(
        self,
        state_path: str = "weights_state.json",
        alpha: float = 0.2,      # EWMA smoothing for accuracy
        beta: float = 0.1,       # EWMA smoothing for variance
        min_weight: float = 0.05 # floor before softmax (keeps diversity)
    ):
        self.path = Path(state_path)
        self.state: Dict = _safe_load_json(self.path)
        self.alpha = alpha
        self.beta = beta
        self.min_weight = min_weight

    def _ensure(self, symbol: str, signal: str) -> None:
        self.state.setdefault(symbol, {})
        self.state[symbol].setdefault(signal, {
            "ema_acc": 0.55,   # start slightly optimistic
            "ema_var": 0.05,   # pseudo-variance of correctness stream
            "count": 0,
            "last_update": 0.0,
            "base": 1.0        # base weight multiplier (manual tweaks if ever needed)
        })

    def register_outcome(self, symbol: str, signal: str, correct: bool) -> None:
        """
        Call this from your strategy AFTER an outcome is known.
        `correct=True` if the signal direction was right, else False.
        """
        self._ensure(symbol, signal)
        s = self.state[symbol][signal]
        x = 1.0 if correct else 0.0

        # EWMA accuracy
        s["ema_acc"] = (1 - self.alpha) * s["ema_acc"] + self.alpha * x

        # EWMA pseudo-variance around the running mean (Bessel-like but EWMA)
        diff = x - s["ema_acc"]
        s["ema_var"] = (1 - self.beta) * s["ema_var"] + self.beta * (diff * diff)

        s["count"] += 1
        s["last_update"] = time.time()
        _safe_dump_json(self.path, self.state)

    def compute(
        self,
        symbol: str,
        signal_names: List[str],
        regime: str | None = None,
        vol: float | None = None
    ) -> Dict[str, float]:
        """
        Returns a dict of normalized weights for the provided `signal_names`.
        """
        # Hyperparams for scoring -> softmax
        w_acc = 3.0       # influence of accuracy
        w_stab = 2.0      # penalty from variance
        w_reg = 1.0       # regime alignment bump
        w_vol = 0.5       # volatility penalty if signal tends to fail in high vol

        # Basic priors if unknown
        regime = regime or "range"
        vol = 0.0 if vol is None else float(vol)

        # Simple regime preference map (you can extend per your naming)
        # Keys must match your signal names in bayes_fusion signals
        regime_bias = {
            "trend": {
                "kf_trend": +1.0, "kf_slope": +1.0, "stoch_momo": +0.5,
                "ou_revert": -0.5, "ou_zscore": -0.4
            },
            "range": {
                "ou_revert": +1.0, "ou_zscore": +0.8,
                "kf_trend": -0.5, "kf_slope": -0.5, "stoch_momo": -0.2
            }
        }
        rb = regime_bias.get(regime, {})

        # Volatility aversion map (which signals struggle when vol climbs)
        vol_penalty = {
            "ou_revert": +1.0, "ou_zscore": +0.6,  # mean-revert worse in high vol
            "kf_trend": 0.2, "kf_slope": 0.1, "stoch_momo": 0.3
        }

        z: Dict[str, float] = {}
        for sig in signal_names:
            self._ensure(symbol, sig)
            s = self.state[symbol][sig]

            acc_term  = w_acc  * (s["ema_acc"] - 0.5) * 2.0          # centered & scaled [-1,1] -> [-2,2] * w_acc
            stab_term = -w_stab * min(1.0, max(0.0, s["ema_var"]))    # lower variance => smaller penalty
            reg_term  = w_reg  * rb.get(sig, 0.0)
            vol_term  = -w_vol * vol_penalty.get(sig, 0.2) * max(0.0, min(0.05, vol)) / 0.05
            base      = s.get("base", 1.0)

            score = acc_term + stab_term + reg_term + vol_term
            # floor for exploration before softmax:
            raw = max(self.min_weight, base * exp(score))
            z[sig] = raw

        # Normalize
        ssum = sum(z.values())
        if ssum <= 0:
            # fallback to uniform
            return {sig: 1.0 / max(1, len(signal_names)) for sig in signal_names}
        return {sig: z[sig] / ssum for sig in signal_names}
