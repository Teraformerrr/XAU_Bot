# D:\XAU_Bot\bot\policy\policy_bridge.py
import json
import logging
from pathlib import Path
from datetime import datetime

logging.basicConfig(
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S"
)


class PolicyBridge:
    """
    Connects Bayesian Policy output → actionable trade command.
    """

    def __init__(self, decision_file="bayes_policy_output.json",
                 min_conf=0.55, max_vol=0.25):
        self.decision_file = Path(decision_file)
        self.min_conf = min_conf
        self.max_vol = max_vol

    def load_decision(self):
        if not self.decision_file.exists():
            logging.error(f"Decision file {self.decision_file} not found.")
            return None

        with open(self.decision_file, "r") as f:
            data = json.load(f)
        return data

    def validate_signal(self, decision):
        conf = decision.get("confidence", 0)
        vol = decision.get("volatility", 1)
        drift = decision.get("drift", False)

        if conf < self.min_conf:
            reason = f"❌ Rejected: low confidence ({conf:.2f})"
            return False, reason
        if vol > self.max_vol:
            reason = f"❌ Rejected: high volatility ({vol:.2f})"
            return False, reason
        if drift:
            reason = "⚠️ Drift detected — waiting for stabilization"
            return False, reason

        return True, "✅ Valid signal"

    def translate_action(self, decision):
        action = decision.get("action", "HOLD").upper()
        conf = decision.get("confidence", 0)
        valid, reason = self.validate_signal(decision)

        if not valid:
            logging.warning(reason)
            return {"execute": False, "reason": reason, "decision": action}

        if action in ["BUY", "SELL"]:
            cmd = {
                "execute": True,
                "action": action,
                "timestamp": datetime.utcnow().isoformat(),
                "confidence": conf,
                "volatility": decision.get("volatility"),
                "thresholds": (decision.get("buy_threshold"),
                               decision.get("sell_threshold"))
            }
            logging.info(f"📤 Execution Trigger → {cmd}")
            return cmd

        logging.info(f"⏸ No action → {action}")
        return {"execute": False, "reason": "Hold/No action"}

    def run(self):
        decision = self.load_decision()
        if not decision:
            return {"execute": False, "reason": "Missing decision file"}
        return self.translate_action(decision)


if __name__ == "__main__":
    bridge = PolicyBridge()
    result = bridge.run()
    print(result)
