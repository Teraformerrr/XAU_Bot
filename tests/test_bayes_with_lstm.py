import logging
import pandas as pd

from bot.policy.policy_bridge import PolicyBridge

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")

if __name__ == "__main__":
    df = pd.read_csv("bot/data/ohlcv_features.csv").dropna().tail(1200)

    # Mock other engines (plug your real outputs here in main loop)
    others = {
        "kf_trend": 0.505,
        "kf_slope": 0.507,
        "stoch_momo": 0.501,
        "ou_revert": 0.495,
        "ou_zscore": 0.500,
    }

    bridge = PolicyBridge()
    result = bridge.decide_and_trigger(df, others, regime="trend", vol=0.10)
    print("Policy Bridge Result →", result)
