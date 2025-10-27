# D:\XAU_Bot\tests\test_policy_bridge.py
from bot.policy.policy_bridge import PolicyBridge
import json

# Example Bayesian decision mock
decision = {
    "confidence": 0.61,
    "volatility": 0.08,
    "drift": False,
    "buy_threshold": 0.555,
    "sell_threshold": 0.445,
    "action": "BUY"
}

# Save to temporary decision file
with open("bayes_policy_output.json", "w") as f:
    json.dump(decision, f)

bridge = PolicyBridge()
result = bridge.run()
print("Policy Bridge Result →", result)
