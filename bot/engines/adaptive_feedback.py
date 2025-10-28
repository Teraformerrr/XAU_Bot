import json
import logging
from datetime import datetime
from pathlib import Path
from bot.scheduler.vol_sync import VolatilitySynchronizer

logger = logging.getLogger(__name__)

class AdaptiveFeedback:
    """
    Phase 6.5 — Feedback-Adaptive Volatility Coupling
    Dynamically adjusts learning speed & priors based on live volatility.
    """

    def __init__(self, alpha_base: float = 0.75, k_conf: float = 1.5, state_path="bayes_state.json"):
        self.alpha_base = alpha_base
        self.k_conf = k_conf
        self.state_path = Path(state_path)
        self.vol_sync = VolatilitySynchronizer()
        self.load_state()
        logger.info(f"🧠 AdaptiveFeedback initialized | α={self.alpha_base:.2f}, k={self.k_conf:.2f}")

    def load_state(self):
        """Load Bayesian state for feedback updates."""
        if self.state_path.exists():
            with open(self.state_path, "r") as f:
                self.state = json.load(f)
        else:
            self.state = {"XAUUSD": {"a": 50.0, "b": 50.0}}
        logger.debug("📖 Bayesian state loaded.")

    def save_state(self):
        with open(self.state_path, "w") as f:
            json.dump(self.state, f, indent=2)

    def update(self, symbol: str, win: bool, conf: float):
        """Apply feedback weighted by volatility."""
        vol = self.vol_sync.get_volatility(default=0.1)
        volatility_factor = max(0.05, min(1.0 / (1 + 5 * vol), 1.0))
        adj_alpha = self.alpha_base * volatility_factor

        entry = self.state.get(symbol, {"a": 50.0, "b": 50.0})
        if win:
            entry["a"] += adj_alpha * conf * self.k_conf
        else:
            entry["b"] += adj_alpha * (1 - conf) * self.k_conf

        self.state[symbol] = entry
        self.save_state()

        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "symbol": symbol,
            "win": win,
            "confidence": conf,
            "volatility": vol,
            "vol_factor": volatility_factor,
            "a": entry["a"],
            "b": entry["b"]
        }
        Path("reports").mkdir(exist_ok=True)
        with open("reports/feedback_log.jsonl", "a") as f:
            f.write(json.dumps(log_entry) + "\n")

        logger.info(
            f"📈 AdaptiveFeedback updated | {symbol} | win={win} | conf={conf:.3f} | "
            f"vol={vol:.3f} | α_eff={adj_alpha:.3f} | a={entry['a']:.1f}, b={entry['b']:.1f}"
        )
        return log_entry
