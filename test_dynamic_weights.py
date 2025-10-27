# D:\XAU_Bot\test_dynamic_weights.py
from bot.engines.bayes_fusion import BayesianFusion

if __name__ == "__main__":
    fusion = BayesianFusion("bayes_state.json", "weights_state.json")

    # 1) Get a decision snapshot
    out = fusion.fused_decision("XAUUSD", kf_slope_value=0.0005, min_trade_conf=0.56)
    print("Decision:", out)

    # 2) Simulate logging outcomes (pretend kf_trend and kf_slope were correct, ou_revert wrong, etc.)
    fusion.register_signal_outcome("XAUUSD", "kf_trend", True)
    fusion.register_signal_outcome("XAUUSD", "kf_slope", True)
    fusion.register_signal_outcome("XAUUSD", "ou_revert", False)
    fusion.register_signal_outcome("XAUUSD", "ou_zscore", False)
    fusion.register_signal_outcome("XAUUSD", "stoch_momo", True)

    # 3) Run again; you should see weights shift toward winners
    out2 = fusion.fused_decision("XAUUSD", kf_slope_value=0.0005, min_trade_conf=0.56)
    print("Decision (after learn):", out2)
