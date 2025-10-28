import logging
import time
import json
from pathlib import Path
from datetime import datetime

from bot.utils.config import load_config
from bot.engines.ai_signal_router import AISignalRouter
from bot.engines.threshold_tuner import ThresholdTuner
from bot.scheduler.smart_execution_engine import SmartExecutionEngine
from bot.scheduler.vol_sync import VolatilitySynchronizer
from bot.engines.adaptive_feedback import AdaptiveFeedback



# ────────────────────────────────────────────────────────────────
# Phase 6.4 — Scheduler-Level Volatility Synchronization
# ────────────────────────────────────────────────────────────────

DECISION_FILE = Path("reports/ai_signal_output.json")
FEEDBACK_FILE = Path("reports/feedback_log.jsonl")


def read_latest_decision():
    """Read the latest AI decision from JSON file."""
    if DECISION_FILE.exists():
        with open(DECISION_FILE, "r") as f:
            return json.load(f)
    raise FileNotFoundError("Decision file not found.")


def fallback_decision(symbol: str, buy_th: float, sell_th: float):
    """
    Generate a fallback decision using the most recent feedback entry.
    Keeps scheduler alive if router output is unavailable.
    """
    conf, vol = 0.50, 0.10
    if FEEDBACK_FILE.exists():
        try:
            with open(FEEDBACK_FILE, "r") as f:
                lines = [ln.strip() for ln in f if ln.strip()]
            if lines:
                last = json.loads(lines[-1])
                conf = float(last.get("confidence", conf))
                vol = float(last.get("volatility", vol))
        except Exception as e:
            logging.warning(f"⚠️ Failed to parse feedback_log.jsonl → using defaults ({e})")

    action = "BUY" if conf >= buy_th else "SELL" if conf <= sell_th else "HOLD"

    decision = {
        "symbol": symbol,
        "action": action,
        "confidence": round(conf, 6),
        "volatility": round(vol, 6),
        "source": "fallback",
        "timestamp": datetime.utcnow().isoformat()
    }

    DECISION_FILE.parent.mkdir(exist_ok=True)
    with open(DECISION_FILE, "w") as f:
        json.dump(decision, f, indent=2)

    logging.info(f"🛟 Fallback decision generated → {decision}")
    return decision


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    logger = logging.getLogger(__name__)
    logger.info("──────────────────────────── Phase 6.4 Scheduler ────────────────────────────")

    # ✅ Load configuration
    config = load_config()
    symbol = "XAUUSD.sd"
    interval = int(config.get("engine", {}).get("bar_seconds", 60))
    mode = config.get("mode", "paper")

    logger.info("✅ YAML config loaded successfully from config.yaml")
    logger.info(f"Symbol: {symbol} | Interval: {interval}s | Mode: {mode}")
    logger.info("──────────────────────────────────────────────────────────────────────────────")

    # 🧩 Initialize modules
    ai_router = AISignalRouter()
    tuner = ThresholdTuner()
    see = SmartExecutionEngine(config)
    af = AdaptiveFeedback()
    vol_sync = VolatilitySynchronizer()

    logger.info("🧠 Scheduler initialized with VolSync, ThresholdTuner, and SmartExecutionEngine.")

    # Detect any callable router method
    router_method = None
    for m in ("run", "activate", "process", "forward", "infer", "predict", "route", "decide", "get_decision"):
        if hasattr(ai_router, m):
            router_method = getattr(ai_router, m)
            logger.info(f"✅ Detected AISignalRouter method: {m}()")
            break
    if not router_method:
        logger.info("ℹ️ AISignalRouter has no callable method; will rely on decision file or fallback.")

    # ────────────────────────────────────────────────────────────────
    # Continuous Scheduler Loop
    # ────────────────────────────────────────────────────────────────
    while True:
        cycle_start = datetime.utcnow().isoformat()
        logger.info("──────────────────────── Scheduler Cycle ────────────────────────")

        # 🌐 Step 1: Volatility Synchronization
        synced_vol = vol_sync.get_volatility()
        logger.info(f"🔁 [VolSync] Unified volatility={synced_vol:.4f} (synced across modules)")

        # 🎯 Step 2: Adaptive Thresholds
        th = tuner.tune()
        buy_th, sell_th = th["buy_th"], th["sell_th"]
        logger.info(f"🎯 Dynamic Thresholds → BUY={buy_th:.3f} | SELL={sell_th:.3f} | win_rate={th['win_rate']:.3f}")

        # 🧠 Step 3: Run AI Router
        try:
            if router_method:
                router_method(symbol)
        except Exception as e:
            logger.warning(f"⚠️ AISignalRouter call failed → {e}")

        # 📖 Step 4: Read Decision or Fallback
        try:
            decision = read_latest_decision()
        except FileNotFoundError:
            logger.info("ℹ️ Decision file not found; creating fallback from feedback_log.jsonl …")
            decision = fallback_decision(symbol, buy_th, sell_th)

        action = decision.get("action", "HOLD")
        conf = float(decision.get("confidence", 0.0))
        vol = float(decision.get("volatility", synced_vol))
        logger.info(f"🧠 Decision: {action} | conf={conf:.3f} | vol={vol:.3f} | src={decision.get('source','router')}")

        # ⚙️ 4. Execute trade
        try:
            payload = {
                "symbol": symbol,
                "action": action,
                "confidence": conf,
                "volatility": vol,
                "timestamp": datetime.utcnow().isoformat()
            }

            if hasattr(see, "execute"):
                result = see.execute(payload)
            else:
                result = {
                    "status": "SIMULATED",
                    "symbol": symbol,
                    "action": action,
                    "conf": conf,
                    "pnl": 0.0  # default simulated pnl
                }

            logging.info(f"✅ Execution result → {result}")

            # 🧠 Step 6.6: Adaptive Feedback Update
            try:
                if isinstance(result, dict):
                    pnl = result.get("pnl", 0.0)
                    win = pnl > 0
                    conf_used = float(payload.get("confidence", 0.5))
                    af.update(symbol, win=win, conf=conf_used)
                else:
                    logging.info("ℹ️ No valid result payload for feedback update.")
            except Exception as e:
                logging.error(f"❌ AdaptiveFeedback update failed: {e}")

        except Exception as e:
            logging.error(f"❌ Execution failed: {e}")

        # 🕒 Step 6: Sleep before next cycle
        sleep_time = max(interval, 10)
        logger.info(f"Cycle completed @ {cycle_start}")
        logger.info(f"⏸️ Sleeping for {sleep_time}s before next cycle …")
        time.sleep(sleep_time)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logging.info("🛑 Scheduler stopped manually.")
