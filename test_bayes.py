import time, yaml
from bot.models import get_bayes_engine
from bot.models.bayes_confidence import SignalEvidence

# 1. Load config safely
with open("D:\\XAU_Bot\\config.yaml", encoding="utf-8") as f:
    config = yaml.safe_load(f)

# 2. Initialize engine
engine = get_bayes_engine(config)

# 3. Simulate evidence (from Kalman, OU, Stoch models)
evidence = {
    "kf_slope": SignalEvidence(True, 0.8),
    "ou_zscore": SignalEvidence(True, 0.6),
    "stoch_momo": SignalEvidence(True, 0.7)
}

# 4. Create fake trade
trade_id = f"XAUUSD:{int(time.time())}"
direction = "buy"

# Register decision
engine.register_decision(trade_id, "XAUUSD", direction, evidence)
print(f"Registered {direction.upper()} trade {trade_id}")

# 5. Simulate outcome (+profit)
engine.update_outcome(trade_id, +100.0)
print(f"Updated outcome for {trade_id}")

# 6. Check updated state file
print("\nCurrent Bayesian state:")
with open("D:\\XAU_Bot\\bot\\state\\bayes_state.json", encoding="utf-8") as f:
    print(f.read())
