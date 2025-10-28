import json
import logging
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class RiskPolicy:
    """Risk policy definition — loaded from config.yaml or default."""
    max_dd_pct: float = 20.0          # Max allowed drawdown %
    max_risk_per_trade_pct: float = 2.0
    max_daily_loss_pct: float = 5.0
    cooldown_minutes: int = 30


class DynamicRiskGovernor:
    """
    Phase 5.2 — Dynamic Risk Governor (DRG)
    Controls whether the bot can trade based on:
    - Portfolio drawdown
    - Daily loss limit
    - Risk per trade
    - Dynamic hedging requests
    """

    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.policy = self._load_policy()
        self.path = Path("risk_state.json")
        self.state = self._load_state()

        # Initialize runtime metrics
        self.mode = cfg.get("mode", "paper")
        self.current_dd = 0.0
        self.daily_loss_pct = 0.0
        self.paused = False
        self.hedge_requested = False

        self._publish_state(initial=True)
        logger.info("🧠 DynamicRiskGovernor initialized | Mode=%s", self.mode)

    # ------------------------------------------------------------------
    def _load_policy(self) -> RiskPolicy:
        """Load policy parameters from config dict."""
        try:
            risk_cfg = self.cfg.get("risk", {})
            return RiskPolicy(
                max_dd_pct=risk_cfg.get("max_dd_pct", 20.0),
                max_risk_per_trade_pct=risk_cfg.get("max_risk_per_trade_pct", 2.0),
                max_daily_loss_pct=risk_cfg.get("max_daily_loss_pct", 5.0),
                cooldown_minutes=risk_cfg.get("cooldown_minutes", 30),
            )
        except Exception as e:
            logger.error("⚠️ Failed to parse risk policy: %s", e)
            return RiskPolicy()

    # ------------------------------------------------------------------
    def _load_state(self):
        """Load saved risk state if it exists."""
        if self.path.exists():
            try:
                with open(self.path, "r") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning("⚠️ Could not load risk_state.json → %s", e)
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "paused": False,
            "drawdown_pct": 0.0,
            "daily_loss_pct": 0.0,
            "hedge_active": False,
        }

    # ------------------------------------------------------------------
    def _save_state(self, data: dict):
        """Save risk state to file."""
        try:
            with open(self.path, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error("❌ Failed to save risk_state.json: %s", e)

    # ------------------------------------------------------------------
    def _publish_state(self, initial=False):
        """Save and log current risk policy snapshot."""
        state = {
            "timestamp": datetime.utcnow().isoformat(),
            "mode": self.mode,
            "max_drawdown": self.current_dd,
            "daily_loss_pct": self.daily_loss_pct,
            "paused": self.paused,
            "hedge_requested": self.hedge_requested,
            "policy": asdict(self.policy)
            if hasattr(self, "policy")
            else (dict(self.cfg) if isinstance(self.cfg, dict) else getattr(self.cfg, "__dict__", {})),
            "status": "initialized" if initial else "updated",
        }
        self._save_state(state)

    # ------------------------------------------------------------------
    def update_metrics(self, equity: float, start_equity: float):
        """Update drawdown & daily loss based on current equity."""
        try:
            dd = round(((start_equity - equity) / start_equity) * 100, 2)
            self.current_dd = max(dd, 0.0)
            logger.debug("📉 Current drawdown: %.2f%%", self.current_dd)
            if self.current_dd >= self.policy.max_dd_pct:
                self.paused = True
                logger.warning(
                    "⏸️ Trading PAUSED → max drawdown %.2f%% ≥ limit %.2f%%",
                    self.current_dd, self.policy.max_dd_pct,
                )
        except Exception as e:
            logger.error("❌ update_metrics() error: %s", e)

    # ------------------------------------------------------------------
    def request_hedge(self, symbol: str, lots: float):
        """Trigger a hedge request when large losses are detected."""
        self.hedge_requested = True
        logger.warning("🛡️ Hedge requested → [%s %.2f lots]", symbol, lots)
        self._publish_state()

    # ------------------------------------------------------------------
    def can_trade(self, symbol: str) -> bool:
        """
        Checks if trading is allowed for the symbol.
        Enforces drawdown and pause conditions.
        """
        try:
            if self.paused:
                logger.warning("⏸️ Trading blocked by DRG (pause active)")
                return False

            if self.current_dd >= self.policy.max_dd_pct:
                logger.warning(
                    "⏸️ Trading PAUSED → max DD %.2f%% ≥ %.2f%%",
                    self.current_dd, self.policy.max_dd_pct,
                )
                self.paused = True
                self._publish_state()
                return False

            # Allow trading otherwise
            return True

        except Exception as e:
            logger.error("❌ can_trade() error → %s", e)
            return False

    # ------------------------------------------------------------------
    def resume_trading(self):
        """Manually resume trading after cooldown."""
        self.paused = False
        self.hedge_requested = False
        logger.info("▶️ Trading RESUMED")
        self._publish_state()

    # ------------------------------------------------------------------
    def __repr__(self):
        return (
            f"<DynamicRiskGovernor mode={self.mode} paused={self.paused} "
            f"DD={self.current_dd:.2f}% daily_loss={self.daily_loss_pct:.2f}%>"
        )
