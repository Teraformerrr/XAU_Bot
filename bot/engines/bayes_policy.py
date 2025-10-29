# D:\XAU_Bot\bot\engines\bayes_policy.py
import json
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")

class BayesianPolicy:
    def __init__(self, config_path="policy_config.json"):
        self.config_path = config_path
        self.policy = self.load_policy()

    def load_policy(self):
        try:
            with open(self.config_path, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            policy = {
                "base_buy": 0.65,
                "base_sell": 0.50,
                "vol_sensitivity": 0.08,
                "drift_penalty": 0.05
            }
            with open(self.config_path, "w") as f:
                json.dump(policy, f, indent=4)
            return policy

    def adjust_thresholds(self, vol: float, drift: bool):
        buy = self.policy["base_buy"]
        sell = self.policy["base_sell"]

        # widen thresholds during high volatility
        buy += vol * self.policy["vol_sensitivity"]
        sell -= vol * self.policy["vol_sensitivity"]

        # penalize confidence if drift detected
        if drift:
            buy += self.policy["drift_penalty"]
            sell -= self.policy["drift_penalty"]

        return buy, sell

    def decide(self, conf: float, vol: float, drift: bool):
        buy_thr, sell_thr = self.adjust_thresholds(vol, drift)

        if conf >= buy_thr:
            action = "BUY"
        elif conf <= sell_thr:
            action = "SELL"
        else:
            action = "HOLD"

        logging.info(f"Policy Decision → conf={conf:.4f} | vol={vol:.3f} | drift={drift} | thresholds=({sell_thr:.3f}, {buy_thr:.3f}) | action={action}")
        return {
            "confidence": conf,
            "volatility": vol,
            "drift": drift,
            "buy_threshold": buy_thr,
            "sell_threshold": sell_thr,
            "action": action
        }

if __name__ == "__main__":
    # 🔬 Example test
    policy = BayesianPolicy()
    decision = policy.decide(conf=0.52, vol=0.2, drift=True)
    print(decision)
