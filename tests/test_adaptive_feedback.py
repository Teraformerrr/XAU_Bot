import logging
from bot.ai_core.adaptive_feedback import AdaptiveFeedback
from bot.utils.config_loader import load_config

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")

if __name__ == "__main__":
    cfg = load_config("config.yaml")
    fb = AdaptiveFeedback(cfg)

    # Simulate a win and a loss to see priors move both ways
    fb.register_trade_outcome(symbol="XAUUSD", action="BUY", pnl=+120.0, confidence=0.78,
                              components={"kf_trend":0.62,"stoch_momo":0.57}, volatility=0.06)
    fb.register_trade_outcome(symbol="XAUUSD", action="SELL", pnl=-80.0, confidence=0.72,
                              components={"kf_trend":0.58,"stoch_momo":0.51}, volatility=0.05)

    print("✅ Feedback updates applied. Check bayes_state.json and reports/feedback_log.jsonl")
