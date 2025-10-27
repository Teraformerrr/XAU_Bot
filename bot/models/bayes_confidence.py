# D:\XAU_Bot\bot\models\bayes_confidence.py
from __future__ import annotations
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Tuple

from bot.utils.prob import logit, sigmoid, clip01

# ---------------------------
# Design
# ---------------------------
# We model trade success as a Bernoulli variable with:
#   logit P(success) = logit(prior) + Σ_i w_i * LR_i
# where LR_i = log( p_i / (1 - p_i) ) if signal_i supports the trade,
#        or = log( (1 - p_i) / p_i ) if signal_i contradicts the trade.
# Each p_i is the reliability of signal i, estimated online with a Beta prior.
#
# Signals expected (but engine is flexible):
#  - kf_trend:     True if Kalman trend agrees with direction; strength in [0..1]
#  - ou_revert:    True if OU mean reversion supports direction; strength in [0..1]
#  - stoch_momo:   True if Stoch momentum agrees; strength in [0..1]
#
# You can add more booleans the same way without changing core math.
#
# Online learning:
#  - After placing a trade, call register_decision(...) to store the evidence.
#  - When the trade closes, call update_outcome(..., realized_pnl) to update Betas.
#
# State is persisted in D:\XAU_Bot\bot\state\bayes_state.json

DEFAULT_ALPHA = 50.0   # strong but not rigid priors; adjust in config if needed
DEFAULT_BETA  = 50.0
DEFAULT_SIGNALS = ("kf_trend", "ou_revert", "stoch_momo")

@dataclass
class SignalEvidence:
    present: Optional[bool]   # True supports, False contradicts, None = ignore
    strength: float = 1.0     # [0..1] scales contribution (quality of the evidence)

class BayesianConfidenceEngine:
    def __init__(self,
                 state_path: Path,
                 default_alpha: float = DEFAULT_ALPHA,
                 default_beta: float = DEFAULT_BETA,
                 signals: Tuple[str, ...] = DEFAULT_SIGNALS,
                 base_prior_alpha: float = DEFAULT_ALPHA,
                 base_prior_beta: float = DEFAULT_BETA):
        self.state_path = state_path
        self.default_alpha = float(default_alpha)
        self.default_beta  = float(default_beta)
        self.signals = tuple(signals)
        self.base_prior_alpha = float(base_prior_alpha)
        self.base_prior_beta  = float(base_prior_beta)

        self.state: Dict[str, dict] = {}  # per-symbol
        self.decisions: Dict[str, dict] = {}  # pending outcomes by trade_id
        self._load()

    # ---------- Persistence ----------
    def _load(self):
        try:
            if self.state_path.exists():
                self.state = json.loads(self.state_path.read_text(encoding="utf-8"))
            else:
                self.state = {}
        except Exception:
            self.state = {}

    def _save(self):
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(json.dumps(self.state, indent=2), encoding="utf-8")

    def _ensure_symbol(self, symbol: str):
        if symbol not in self.state:
            self.state[symbol] = {
                "prior": {"a": self.base_prior_alpha, "b": self.base_prior_beta},
                "signals": {
                    s: {"a": self.default_alpha, "b": self.default_beta}
                    for s in self.signals
                }
            }

    # ---------- Read helpers ----------
    @staticmethod
    def _beta_mean(a: float, b: float) -> float:
        return a / max(a + b, 1e-12)

    def _signal_p(self, symbol: str, sig: str) -> float:
        a = float(self.state[symbol]["signals"][sig]["a"])
        b = float(self.state[symbol]["signals"][sig]["b"])
        return clip01(self._beta_mean(a, b))

    def _prior_p(self, symbol: str) -> float:
        a = float(self.state[symbol]["prior"]["a"])
        b = float(self.state[symbol]["prior"]["b"])
        return clip01(self._beta_mean(a, b))

    # ---------- Core inference ----------
    def compute_confidence(self,
                           symbol: str,
                           direction: str,
                           evidence: Dict[str, SignalEvidence]) -> Dict[str, float]:
        """
        Returns a dict with:
          - confidence: P(success) in [0..1]
          - log_odds:   uncalibrated sum
          - prior:      prior success probability used
        """
        direction = direction.lower()
        assert direction in ("buy", "sell")

        self._ensure_symbol(symbol)

        prior = self._prior_p(symbol)              # base win rate for this symbol
        log_odds = logit(prior)
        # Per-signal contribution
        for sig_name, sig_ev in evidence.items():
            if sig_name not in self.state[symbol]["signals"]:
                # allow dynamic extension (new signals)
                self.state[symbol]["signals"][sig_name] = {"a": self.default_alpha, "b": self.default_beta}

            if sig_ev.present is None:
                continue

            p_sig = self._signal_p(symbol, sig_name)
            # Likelihood ratio in log-space, scaled by strength
            lr = math.log(p_sig / (1.0 - p_sig + 1e-12) + 1e-12)
            if sig_ev.present is True:
                contribution = sig_ev.strength * lr
            else:
                contribution = sig_ev.strength * (-lr)
            log_odds += contribution

        confidence = sigmoid(log_odds)
        return {
            "confidence": float(confidence),
            "log_odds": float(log_odds),
            "prior": float(prior),
        }

    # ---------- Decision tracking / online updates ----------
    def register_decision(self,
                          trade_id: str,
                          symbol: str,
                          direction: str,
                          evidence: Dict[str, SignalEvidence]):
        """Call this right before you place the order."""
        self._ensure_symbol(symbol)
        self.decisions[trade_id] = {
            "symbol": symbol,
            "direction": direction.lower(),
            "evidence": {
                k: {"present": v.present, "strength": float(v.strength)}
                for k, v in evidence.items()
            }
        }

    def update_outcome(self, trade_id: str, realized_pnl: float):
        """
        Call this once per trade when it closes.
        realized_pnl > 0 means success, <=0 means fail.
        We update the prior and every signal Beta where evidence.present was True/False.
        Strength scales how much we nudge the Beta (fractional updates).
        """
        if trade_id not in self.decisions:
            return  # unknown trade; silently ignore

        dec = self.decisions.pop(trade_id)
        symbol = dec["symbol"]
        self._ensure_symbol(symbol)

        success = realized_pnl > 0.0
        sym_state = self.state[symbol]

        # Update prior first
        if success:
            sym_state["prior"]["a"] = float(sym_state["prior"]["a"]) + 1.0
        else:
            sym_state["prior"]["b"] = float(sym_state["prior"]["b"]) + 1.0

        # Update signals with fractional counts based on strength
        for sig_name, ev in dec["evidence"].items():
            present = ev["present"]
            strength = float(ev.get("strength", 1.0))
            if present is None:
                continue

            if sig_name not in sym_state["signals"]:
                sym_state["signals"][sig_name] = {"a": self.default_alpha, "b": self.default_beta}

            rec = sym_state["signals"][sig_name]
            if present is True:
                # If signal supported the trade, reward a on success, b on failure
                if success:
                    rec["a"] = float(rec["a"]) + strength
                else:
                    rec["b"] = float(rec["b"]) + strength
            else:
                # If signal contradicted the trade, flip the credit
                if success:
                    rec["b"] = float(rec["b"]) + strength
                else:
                    rec["a"] = float(rec["a"]) + strength

        # Persist
        self._save()

    # ---------- Utility: build evidence from raw features ----------
    @staticmethod
    def build_evidence_from_features(direction: str,
                                     kf_slope: Optional[float] = None,
                                     kf_slope_scale: float = 5.0,
                                     ou_zscore: Optional[float] = None,
                                     ou_entry_z: float = 1.0,
                                     stoch_fast: Optional[float] = None,
                                     stoch_slow: Optional[float] = None) -> Dict[str, SignalEvidence]:
        """
        Converts raw model outputs into {signal: SignalEvidence}.

        - Kalman trend: supports BUY if slope > 0, SELL if slope < 0.
          strength ~ tanh(|slope| / kf_slope_scale).
        - OU mean reversion: supports BUY if z < -ou_entry_z (expect up), SELL if z > ou_entry_z.
          strength ~ min(|z| / 3, 1).
        - Stochastic momentum: supports BUY if fast>slow, SELL otherwise.
          strength ~ min(|fast - slow| / 20, 1)   # difference of %K-%D, 0..100 range
        """
        direction = direction.lower()
        assert direction in ("buy", "sell")

        ev: Dict[str, SignalEvidence] = {}

        # Kalman trend
        if kf_slope is None:
            ev["kf_trend"] = SignalEvidence(None, 0.0)
        else:
            agree = (kf_slope > 0 and direction == "buy") or (kf_slope < 0 and direction == "sell")
            strength = math.tanh(abs(kf_slope) / max(kf_slope_scale, 1e-6))
            ev["kf_trend"] = SignalEvidence(agree, float(strength))

        # OU mean reversion
        if ou_zscore is None:
            ev["ou_revert"] = SignalEvidence(None, 0.0)
        else:
            support_buy = (ou_zscore <= -abs(ou_entry_z))
            support_sell = (ou_zscore >=  abs(ou_entry_z))
            present = None
            if direction == "buy" and support_buy:
                present = True
            elif direction == "sell" and support_sell:
                present = True
            else:
                # If we're clearly in the opposite extreme, count as contradict
                if direction == "buy" and support_sell:
                    present = False
                elif direction == "sell" and support_buy:
                    present = False
                else:
                    present = None
            strength = min(abs(ou_zscore) / 3.0, 1.0)
            ev["ou_revert"] = SignalEvidence(present, float(strength))

        # Stochastic momentum
        if stoch_fast is None or stoch_slow is None:
            ev["stoch_momo"] = SignalEvidence(None, 0.0)
        else:
            agree = (stoch_fast > stoch_slow and direction == "buy") or \
                    (stoch_fast < stoch_slow and direction == "sell")
            strength = min(abs((stoch_fast - stoch_slow)) / 20.0, 1.0)
            ev["stoch_momo"] = SignalEvidence(agree, float(strength))

        return ev


# -------- Convenience factory --------
_engine_singleton: Optional[BayesianConfidenceEngine] = None

def get_bayes_engine(config: dict) -> BayesianConfidenceEngine:
    """
    Create or reuse a process-level singleton so every module shares one engine.
    Expect config['bayes'] section (see config.yaml snippet).
    """
    global _engine_singleton
    if _engine_singleton is not None:
        return _engine_singleton

    root = Path(config.get("paths", {}).get("root_dir", "."))
    state_dir = root / "bot" / "state"
    state_path = state_dir / "bayes_state.json"

    bayes_cfg = config.get("bayes", {})
    _engine_singleton = BayesianConfidenceEngine(
        state_path=state_path,
        default_alpha=float(bayes_cfg.get("signal_alpha", DEFAULT_ALPHA)),
        default_beta=float(bayes_cfg.get("signal_beta", DEFAULT_BETA)),
        signals=tuple(bayes_cfg.get("signals", list(DEFAULT_SIGNALS))),
        base_prior_alpha=float(bayes_cfg.get("prior_alpha", DEFAULT_ALPHA)),
        base_prior_beta=float(bayes_cfg.get("prior_beta", DEFAULT_BETA)),
    )
    return _engine_singleton
