# D:\XAU_Bot\bot\runtime\live_loop.py
if __name__ == "__main__":
    print("⚠️  live_loop.py should not be executed directly. Use main.py instead.")
    raise SystemExit


import logging
import yaml
import math
import pandas as pd
from typing import Dict

from bot.policy.policy_bridge import PolicyBridge
from bot.execution.live_executor import LiveExecutor
from bot.runtime.live_guardrails import TradeGuard


# Optional portfolio trade logging if available
try:
    from bot.portfolio.trade_logger import log_trade  # your existing logger
except Exception:
    log_trade = None

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")

REQ_FEATURES = ["EMA_20","EMA_50","EMA_200","RSI_14","MACD","BB_upper","BB_lower","ATR"]

def load_config(path: str = "config.yaml") -> Dict:
    with open(path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    logging.info("✅ config.yaml loaded")
    return cfg

def normalized_vol_from_atr(df: pd.DataFrame) -> float:
    # Simple 0..1 proxy using ATR / median(close) windowed
    try:
        atr = df["ATR"].tail(200).median()
        ref = df["close"].tail(200).median()
        vol = max(0.0, min(1.0, float(atr / max(ref, 1e-9)) * 50))  # scale factor to keep within [0,1]
        return vol
    except Exception:
        return 0.1

def risk_size_from_config(cfg: Dict, equity: float, atr: float, pip_value_usd: float = 1.0) -> float:
    """
    Very conservative position sizing:
    - risk $ = equity * max_risk_per_trade_pct
    - stop distance = sl_atr_mult * ATR
    - volume ≈ risk$ / (stop_distance * pip_value)
    Clamp to [0.01, 5] lots to avoid extremes in demo.
    """
    risk_pct = float(cfg.get("max_risk_per_trade_pct", 1)) / 100.0
    sl_mult = float(cfg.get("risk", {}).get("sl_atr_mult", 1.5))
    risk_dollars = max(10.0, equity * risk_pct)
    stop_dist = max(0.1, sl_mult * atr)
    raw = risk_dollars / (stop_dist * max(pip_value_usd, 1e-6))
    lots = max(0.01, min(5.0, round(raw, 2)))
    return lots

def latest_feature_frame() -> pd.DataFrame:
    df = pd.read_csv("bot/data/ohlcv_features.csv").dropna()
    missing = [c for c in (REQ_FEATURES + ["close"]) if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    return df

def main():
    cfg = load_config()
    mode = cfg.get("mode", "paper")
    symbol = "XAUUSD"
    equity = float(cfg.get("start_equity", 100000))

    bridge = PolicyBridge()
    executor = LiveExecutor(mode=mode)
    guard = TradeGuard("config.yaml")

    # Prepare "other components" — in production you’d pull from your engines
    def compute_other_components(df: pd.DataFrame) -> Dict[str, float]:
        # Placeholder: neutral-ish confidences; replace with live engine outputs you already have
        return {
            "kf_trend": 0.50,
            "kf_slope": 0.50,
            "stoch_momo": 0.50,
            "ou_revert": 0.50,
            "ou_zscore": 0.50,
        }

    # One-shot loop (call repeatedly in your scheduler)
    df = latest_feature_frame()
    others = compute_other_components(df)
    vol = normalized_vol_from_atr(df)

    decision = bridge.decide_and_trigger(
        latest_df=df,
        other_components=others,
        regime="trend",   # swap with your regime detector
        vol=vol
    )

    if decision["execute"]:
        # Risk parameters
        atr = float(df["ATR"].tail(200).median())
        lots = risk_size_from_config(cfg, equity, atr, pip_value_usd=1.0)

        # Basic SL/TP using ATR multiples from config
        risk_cfg = cfg.get("risk", {})
        sl_mult = float(risk_cfg.get("sl_atr_mult", 1.5))
        tp_mult = float(risk_cfg.get("tp_atr_mult", 2.2))
        last_close = float(df["close"].iloc[-1])

        if decision["action"] == "BUY":
            sl = last_close - sl_mult * atr
            tp = last_close + tp_mult * atr
        else:
            sl = last_close + sl_mult * atr
            tp = last_close - tp_mult * atr

        # Place order (paper or live)
        order = executor.send_order(
            symbol=symbol,
            action=decision["action"],
            volume=lots,
            price=None,
            sl=round(sl, 2),
            tp=round(tp, 2),
            comment=f"LSTM-Fused | conf={decision['confidence']}"
        )

        # Log portfolio impact (if your logger exists)
        if log_trade:
            pnl = 0.0
            log_trade(
                symbol=symbol,
                action=decision["action"],
                confidence=float(decision["confidence"]),
                volatility=float(decision["volatility"]),
                volume=float(lots),
                price=last_close,
                pnl=pnl,
                status=order.get("status", "SIMULATED")
            )

    else:
        logging.info("🟡 HOLD — no execution this tick (inside adaptive band).")

# if __name__ == "__main__":
#     main()
