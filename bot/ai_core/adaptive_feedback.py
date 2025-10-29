import json
import logging
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


def _clamp(v, lo, hi): return max(lo, min(hi, v))


class AdaptiveFeedback:
    """
    Phase 6.2 – Adaptive Decision Feedback Loop
    - Reads/writes bayes_state.json
    - After each trade, nudges Beta priors (a,b) for:
        * Global prior for the symbol
        * Individual signal priors (if provided)
    - Weight of the nudge depends on confidence & outcome (PnL)
    """

    def __init__(self, config: dict, bayes_path: str = "bayes_state.json", log_path: str = "reports/feedback_log.jsonl"):
        self.cfg = config or {}
        self.bayes_path = Path(bayes_path)
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self.state = self._load_bayes()

        # Feedback scaling (safe defaults if not in config)
        fb_cfg = (self.cfg.get("feedback") or {})
        self.k_conf = float(fb_cfg.get("confidence_gain", 1.5))   # scales confidence effect
        self.alpha = float(fb_cfg.get("update_strength", 0.75))   # per-trade update magnitude
        self.max_a_b = int(fb_cfg.get("max_prior_total", 2500))   # cap to avoid runaway

        logger.info("🧠 AdaptiveFeedback ready | alpha=%.2f | k_conf=%.2f", self.alpha, self.k_conf)

    # ------------------------------------------------------------------
    def _load_bayes(self) -> dict:
        if not self.bayes_path.exists():
            logger.warning("⚠️ %s not found; initializing new Bayesian state.", self.bayes_path)
            return {}
        try:
            with open(self.bayes_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error("❌ Failed to load %s → %s", self.bayes_path, e)
            return {}

    def _save_bayes(self):
        try:
            with open(self.bayes_path, "w", encoding="utf-8") as f:
                json.dump(self.state, f, indent=2)
        except Exception as e:
            logger.error("❌ Failed to save %s → %s", self.bayes_path, e)

    def _append_log(self, row: dict):
        try:
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(row) + "\n")
        except Exception as e:
            logger.error("❌ Failed to write %s → %s", self.log_path, e)

    # ------------------------------------------------------------------
    def _ensure_symbol(self, symbol: str):
        if symbol not in self.state:
            self.state[symbol] = {
                "prior": {"a": 50.0, "b": 50.0},
                "signals": {}
            }
        if "prior" not in self.state[symbol]:
            self.state[symbol]["prior"] = {"a": 50.0, "b": 50.0}
        if "signals" not in self.state[symbol]:
            self.state[symbol]["signals"] = {}

    def _nudge_beta(self, node: dict, success_w: float, failure_w: float):
        # Apply alpha-scaled update
        node["a"] = float(node.get("a", 50.0)) + self.alpha * success_w
        node["b"] = float(node.get("b", 50.0)) + self.alpha * failure_w
        # Soft cap (renormalize if too large)
        total = node["a"] + node["b"]
        if total > self.max_a_b:
            scale = self.max_a_b / total
            node["a"] *= scale
            node["b"] *= scale

    # ------------------------------------------------------------------
    def register_trade_outcome(
        self,
        *,
        symbol: str,
        action: str,
        pnl: float,
        confidence: float,
        components: dict | None = None,
        volatility: float | None = None,
        timestamp: str | None = None,
    ):
        """
        Record one trade outcome and update Bayesian priors.

        Params
        - symbol/action/pnl/confidence required
        - components: optional dict of component confidences, e.g.
            {"kf_trend":0.51,"ou_revert":0.47,"stoch_momo":0.56,...}
          If provided, each component Beta prior nudged too.
        - volatility optional (for logging only)
        """
        self._ensure_symbol(symbol)

        # Convert outcome to weighted success/failure in [0.1..0.9]
        # Higher confidence should amplify both win and loss learning.
        conf = _clamp(float(confidence), 0.0, 1.0)
        conf_boost = _clamp(0.5 + (conf - 0.5) * self.k_conf, 0.1, 0.9)

        is_win = pnl > 0.0
        success_w = conf_boost if is_win else (1.0 - conf_boost)
        failure_w = (1.0 - success_w)

        # 1) Update global prior for the symbol
        self._nudge_beta(self.state[symbol]["prior"], success_w, failure_w)

        # 2) Update component priors if provided
        if components and isinstance(components, dict):
            for key, comp_conf in components.items():
                if key not in self.state[symbol]["signals"]:
                    self.state[symbol]["signals"][key] = {"a": 50.0, "b": 50.0}

                # If component had its own confidence, weight by that too (optional)
                c = float(comp_conf) if isinstance(comp_conf, (int, float)) else conf
                c_boost = _clamp(0.5 + (c - 0.5) * self.k_conf, 0.1, 0.9)
                succ = c_boost if is_win else (1.0 - c_boost)
                fail = 1.0 - succ
                self._nudge_beta(self.state[symbol]["signals"][key], succ, fail)

        # Persist & log
        self._save_bayes()
        self._append_log({
            "t": timestamp or datetime.utcnow().isoformat(),
            "symbol": symbol,
            "action": action,
            "pnl": pnl,
            "confidence": conf,
            "volatility": volatility,
            "success_w": round(success_w, 4),
            "failure_w": round(failure_w, 4),
        })

        def update(self, symbol, win, confidence_value, volatility_value):
            """
            Updates Bayesian priors based on trade outcome, confidence, and volatility.
            """
            import datetime

            # Decay existing priors
            self.state[symbol]["a"] *= self.decay
            self.state[symbol]["b"] *= self.decay

            # Update based on outcome
            if win:
                self.state[symbol]["a"] += confidence_value * self.k
            else:
                self.state[symbol]["b"] += confidence_value * self.k

            # Save update
            self.save_state()

            # Log entry
            print(
                f"📈 AdaptiveFeedback updated | {symbol} | win={win} | conf={confidence_value:.3f} | vol={volatility_value:.3f} | a={self.state[symbol]['a']:.1f}, b={self.state[symbol]['b']:.1f}")
            return {
                "timestamp": datetime.datetime.utcnow().isoformat(),
                "symbol": symbol,
                "win": win,
                "confidence": confidence_value,
                "volatility": volatility_value,
                "a": self.state[symbol]["a"],
                "b": self.state[symbol]["b"]
            }

        logger.info("📈 AdaptiveFeedback updated priors | %s | win=%s | conf=%.3f | a=%.1f b=%.1f",
                    symbol, is_win, conf,
                    self.state[symbol]["prior"]["a"], self.state[symbol]["prior"]["b"])
