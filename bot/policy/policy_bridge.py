"""
policy_bridge.py
────────────────────────────────────────────────────────────
Bridge between Bayesian policy and AI signal router.
This ensures trade direction (BUY/SELL/HOLD) decisions
are consistent with thresholds and volatility logic.
────────────────────────────────────────────────────────────
"""

import logging
from bot.engines.bayes_policy import BayesianPolicy

# Configure logger for this module
logger = logging.getLogger(__name__)


class PolicyBridge:
    """
    Bridge between AI router outputs and Bayesian policy thresholds.
    Handles decision-making consistency based on model confidence,
    volatility, and detected market drift.
    """

    def __init__(self):
        # Initialize the underlying BayesianPolicy engine
        self.policy = BayesianPolicy()
        logger.info("✅ PolicyBridge initialized")

    def decide(self, confidence: float, volatility: float, drift: bool = False):
        """
        Forward confidence + volatility through BayesianPolicy → decision.
        Returns a context dictionary used by the higher-level scheduler.
        """
        try:
            decision = self.policy.decide(confidence, volatility, drift)
            logger.info(
                f"📊 Policy Decision → conf={confidence:.3f} | vol={volatility:.3f} | "
                f"drift={drift} | thresholds=({decision['sell_threshold']:.3f}, "
                f"{decision['buy_threshold']:.3f}) | action={decision['action']}"
            )
            return decision

        except Exception as e:
            logger.exception(f"❌ PolicyBridge decision error: {e}")
            return {
                "confidence": confidence,
                "volatility": volatility,
                "action": "HOLD",
                "buy_threshold": 0.80,
                "sell_threshold": 0.50,
                "drift": drift,
            }

    def run(self):
        """
        Wrapper for test and compatibility.
        Loads sample values and calls decide().
        This method allows standalone execution during testing.
        """
        logger.info("🔗 PolicyBridge.run() called – using default test inputs.")
        confidence = 0.6
        volatility = 0.1
        drift = False

        result = self.decide(confidence, volatility, drift)
        logger.info(f"📤 PolicyBridge.run() → {result}")
        return result


# Optional: allow direct run from command line
if __name__ == "__main__":
    bridge = PolicyBridge()
    output = bridge.run()
    print("PolicyBridge Output:", output)
