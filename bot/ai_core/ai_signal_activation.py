import logging
from datetime import datetime
from bot.engines.ai_signal_router import AISignalRouter
from bot.scheduler.smart_execution_engine import SmartExecutionEngine
from bot.risk.dynamic_governor import DynamicRiskGovernor
from bot.utils.state_manager import PortfolioState
from bot.ai_core.adaptive_feedback import AdaptiveFeedback   # ← NEW

logger = logging.getLogger(__name__)

class AISignalActivation:
    """
    Phase 6.1 – AI Signal Activation + Phase 6.2 Feedback hook
    """

    def __init__(self, config):
        self.config = config
        self.router = AISignalRouter(config)
        self.executor = SmartExecutionEngine(config)
        self.risk_governor = DynamicRiskGovernor(config)
        self.portfolio_state = PortfolioState("portfolio_state.json")
        self.feedback = AdaptiveFeedback(config)              # ← NEW

        logger.info("🧠 AISignalActivation initialized | Mode=%s", config.get("mode", "paper"))

    def evaluate_and_execute(self, symbol: str):
        """Evaluate model signals → risk filter → execute → feedback learn."""
        try:
            signal = self.router.get_signal(symbol)
            conf, vol, action = signal["confidence"], signal["volatility"], signal["action"]
            components = signal.get("components")  # router may include component confidences

            logger.info("🤖 %s | AI Decision → %s | Conf=%.3f | Vol=%.3f", symbol, action, conf, vol)

            # Step 1 – Risk check
            if not self.risk_governor.can_trade(symbol):
                logger.warning("⏸️ Trade blocked by DRG for %s", symbol)
                return {"status": "blocked", "reason": "risk_governor"}

            # Step 2 – Decision threshold
            min_conf = self.config.get("engine", {}).get("min_confidence", 0.55)
            if conf < min_conf:
                logger.info("⚠️ Confidence below threshold %.2f → HOLD", min_conf)
                return {"status": "hold", "reason": "low_confidence"}

            # Step 3 – Execute trade
            if action in ["BUY", "SELL"]:
                trade_result = self.executor.execute_trade(symbol, action, conf, vol)
                self.portfolio_state.update_from_trade(trade_result)

                # ---- PHASE 6.2 FEEDBACK (NEW) ----
                self.feedback.register_trade_outcome(
                    symbol=symbol,
                    action=action,
                    pnl=float(trade_result.get("pnl", 0.0)),
                    confidence=float(conf),
                    components=components,                              # if provided
                    volatility=float(vol),
                    timestamp=trade_result.get("timestamp"),
                )
                # -----------------------------------

                return {"status": "executed", "action": action, "trade": trade_result}
            else:
                logger.info("🕊️ No trade action triggered → HOLD")
                return {"status": "hold"}

        except Exception as e:
            logger.error("❌ Signal activation error for %s → %s", symbol, e)
            return {"status": "error", "message": str(e)}
