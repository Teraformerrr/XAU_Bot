# ─────────────────────────────────────────────────────────────────────────────
#  XAU_Bot Scheduler Main – Phase 6.7 (Live Bridge + Position Lifecycle)
#  Author : Mohamed Jamshed
# ─────────────────────────────────────────────────────────────────────────────

from __future__ import annotations
import time
import MetaTrader5 as mt5
from loguru import logger
import os
from dotenv import load_dotenv

from bot.utils.config import load_yaml_config
from bot.engines.ai_signal_router import AISignalRouter
from bot.engines.adaptive_feedback import AdaptiveFeedback
from bot.executors.mt5_executor_adapter import MT5ExecutorAdapter
from bot.executors.smart_trade_executor import SmartTradeExecutor, ExecContext
from bot.executors.position_manager import PositionManager
from bot.executors.trade_feedback_monitor import TradeFeedbackMonitor   # ← NEW


# (optional) risk controllers
try:
    from bot.risk.dynamic_governor import DynamicRiskGovernor
    from bot.risk.smart_exposure import SmartExposureController
except Exception:
    DynamicRiskGovernor = None
    SmartExposureController = None

# ── Init ────────────────────────────────────────────────────────────────────
load_dotenv()
CONFIG_PATH = os.getenv("CONFIG_PATH", "config.yaml")

logger.info("───────────────────────────── Phase 6.6 Scheduler ─────────────────────────────")
config = load_yaml_config(CONFIG_PATH)
logger.info("✅ YAML config loaded successfully")

symbol   = config.get("symbol", "XAUUSD.sd")
interval = int(config.get("interval", 60))     # seconds
mode     = config.get("mode", "mt5")

logger.info(f"Symbol : {symbol} | Interval : {interval}s | Mode : {mode}")
logger.info("──────────────────────────────────────────────────────────────────────────────")

# Engines
ai_signal_router = AISignalRouter()
feedback_engine = AdaptiveFeedback()

# Initialize MT5 executor (for live/demotrading)
executor = MT5ExecutorAdapter()

# Initialize Position Manager (handles SL/TP + trailing logic)
pm = PositionManager(adapter=executor, symbol=symbol)
from bot.executors.smart_trade_executor import SmartTradeExecutor
ste = SmartTradeExecutor()




# Create a PositionManager instance
pm = PositionManager(adapter=executor, symbol=symbol)


feedback_monitor = TradeFeedbackMonitor(feedback_engine, symbol)  # ← NEW

drg = DynamicRiskGovernor() if DynamicRiskGovernor else None
sec = SmartExposureController() if SmartExposureController else None



# ── Main Loop ───────────────────────────────────────────────────────────────
def run_scheduler():
    logger.info("🕒 Scheduler started – Live Bridge Integration active")
    position_lock = False
    while True:
        try:

            # === STEP 0: Trade Lock Check (prevents new trades while any are open) ===
            open_positions = pm.get_open_positions(symbol)
            if open_positions:
                if not position_lock:
                    position_lock = True
                    logger.info(f"🛑 Skipped → open position(s) detected for {symbol}. Trade lock activated.")
                else:
                    logger.info(f"🔒 Trade lock active → waiting for existing position(s) to close.")
                time.sleep(30)
                continue
            else:
                if position_lock:
                    logger.info(f"✅ All positions closed → trade lock released.")
                    position_lock = False

            # === STEP 1: Compute AI confidence & volatility ===
            confidence = ai_signal_router.compute_confidence(symbol)
            latest_volatility = ai_signal_router.compute_volatility(symbol)

            # 🧠 Step 2: Make decision based on current AI signal
            decision = ai_signal_router.make_decision(confidence, vol=latest_volatility, mode="static")

            # 🧩 Step 3: Apply confidence gates
            min_conf, max_conf = 0.70, 0.30  # your thresholds

            buy_ok = (confidence >= min_conf)
            sell_ok = (confidence <= max_conf)

            if not (buy_ok or sell_ok):
                logger.info(
                    f"🕒 Skipped (low confidence) → action={decision['action']} | conf={confidence:.3f} | gate=[BUY≥{min_conf}, SELL≤{max_conf}]")
            else:
                logger.info(
                    f"📩 AI Decision → {decision['action']} | conf={confidence:.3f} | vol={latest_volatility:.3f}")

            # ── NEW: static confidence gate (BUY ≥ min_conf, SELL ≤ 1 - min_conf)
            dec_cfg = config.get("decision", {}) if isinstance(config, dict) else {}
            mode = (dec_cfg.get("mode") or "static").lower()
            min_conf = float(dec_cfg.get("min_conf", 0.70))
            max_conf = float(dec_cfg.get("max_conf", 0.30))
            buy_ok = (confidence >= min_conf)
            sell_ok = (confidence <= max_conf)

            # ...

            # 4) Execute (string or dict decisions) with the gate
            latest_action = None
            if isinstance(decision, str):
                act = decision.upper()
                if act == "BUY" and buy_ok:
                    latest_action = "BUY"
                    ctx = ExecContext(action=latest_action, confidence=float(conf), volatility=float(vol), lot=None)
                    exec_res = ste.execute(ctx)
                    logger.info(f"🔗 STE result → {exec_res}")
                elif act == "SELL" and sell_ok:
                    latest_action = "SELL"
                    ctx = ExecContext(action=latest_action, confidence=float(conf), volatility=float(vol), lot=None)
                    exec_res = ste.execute(ctx)
                    logger.info(f"🔗 STE result → {exec_res}")
                else:
                    logger.info(
                        f"🕒 Skipped (low confidence) → action={act} | conf={confidence:.3f} | gate=[BUY≥{min_conf:.2f}, SELL≤{1 - min_conf:.2f}]")

            elif isinstance(decision, dict):
                act = decision.get("action", "HOLD").upper()
                # Use explicit conf/vol from router if provided; else fallback to measured
                dconf = float(decision.get("confidence", confidence))
                dvol = float(decision.get("volatility", latest_volatility))

                if act == "BUY" and (dconf >= min_conf):
                    latest_action = "BUY"
                    ctx = ExecContext(action=latest_action, confidence=float(confidence), volatility=float(latest_volatility), lot=None)
                    exec_res = ste.execute(ctx)
                    logger.info(f"🔗 STE result → {exec_res}")
                elif act == "SELL" and (dconf <= (1.0 - min_conf)):
                    latest_action = "SELL"
                    ctx = ExecContext(action=latest_action, confidence=dconf, volatility=dvol, lot=None)
                    exec_res = ste.execute(ctx)
                    logger.info(f"🔗 STE result → {exec_res}")
                else:
                    logger.info(
                        f"🕒 Skipped (low confidence) → action={act} | conf={dconf:.3f} | gate=[BUY≥{min_conf:.2f}, SELL≤{1 - min_conf:.2f}]")
            else:
                logger.warning(f"Unexpected decision type: {type(decision)}")


            # ─ Step 4: Execute trade if no open positions ─
            if isinstance(decision, str):
                act = decision.upper()
                if act == "BUY" and buy_ok:
                    latest_action = "BUY"
                    ctx = ExecContext(action=latest_action, confidence=float(confidence),
                                      volatility=float(latest_volatility), lot=None)
                    exec_res = ste.execute(ctx)
                    logger.info(f"🔗 STE result → {exec_res}")
                elif act == "SELL" and sell_ok:
                    latest_action = "SELL"
                    ctx = ExecContext(action=latest_action, confidence=float(confidence),
                                      volatility=float(latest_volatility), lot=None)
                    exec_res = ste.execute(ctx)
                    logger.info(f"🔗 STE result → {exec_res}")
                else:
                    logger.info(
                        f"🕒 Skipped (low confidence) → action={act} | conf={confidence:.3f} | gate=[BUY≥{min_conf:.2f}, SELL≤{1 - min_conf:.2f}]")

            # 6) Poll closed trades → update AdaptiveFeedback with real outcomes
            feedback_monitor.poll_closed_trades()

            # 7) Sleep
            # --- DAILY PROFIT TARGET CHECK ---
            # Load current equity (either live from MT5 or from your portfolio_state.json)
            def load_portfolio_equity():
                try:
                    import json, os
                    path = os.path.join("D:\\XAU_Bot", "portfolio_state.json")
                    if os.path.exists(path):
                        with open(path, "r") as f:
                            data = json.load(f)
                            return data.get("equity", 0)
                except Exception as e:
                    logger.warning(f"⚠️ Could not read portfolio equity: {e}")
                return 0

            # === Fetch Live Equity and Compute Daily Target ===
            try:
                import MetaTrader5 as mt5
                account_info = mt5.account_info()
                if account_info:
                    current_equity = float(account_info.equity)
                    initial_equity = float(account_info.balance)  # use balance as base
                else:
                    logger.warning("⚠️ Could not fetch MT5 account info; using fallback equity = 37000")
                    initial_equity = 37000.0
                    current_equity = initial_equity

                # === Define profit target ===
                target_pct = 0.10  # 2% daily target — change this value as you wish
                target_equity = initial_equity * (1 + target_pct)

                # === Log current state ===
                logger.info(f"💰 Current Equity = {current_equity:.2f} | Target = {target_equity:.2f}")

                # === Check if daily target reached ===
                if current_equity >= target_equity:
                    logger.info(f"🎯 Daily profit target reached ({target_pct * 100:.1f}%). Pausing trading for today.")
                    return  # safely exit today's session

                # === Continue scheduler ===
                logger.info("🕒 Sleeping 30s before next cycle …")
                time.sleep(30)

            except KeyboardInterrupt:
                logger.warning("🧭 Scheduler terminated manually.")
                break
            except Exception as e:
                logger.exception(f"⚠️ Scheduler error: {e}")
                time.sleep(interval)




        except KeyboardInterrupt:
            logger.warning("🧭 Scheduler terminated manually.")
            break
        except Exception as e:
            logger.exception(f"⚠️ Scheduler error: {e}")
            time.sleep(interval)


if __name__ == "__main__":
    run_scheduler()
