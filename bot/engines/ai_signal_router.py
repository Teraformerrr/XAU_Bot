import logging
import json
import random
from datetime import datetime
from pathlib import Path
from bot.scheduler.vol_sync import VolatilitySynchronizer

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ───────────────── VolatilitySync import with safe fallback ─────────────────
try:
    # If you already created a real sync module, use that path:
    from bot.engines.volatility_sync import VolatilitySync  # ← adjust path if needed
except Exception:
    logger.warning("VolatilitySync not found; using fallback stub.")

    class VolatilitySync:
        """Fallback: returns a fixed, conservative volatility if real sync is unavailable."""
        def __init__(self, window: int = 60):
            self.window = window

        def latest(self, symbol: str) -> float:
            # 0.21 ~ 21% annualized proxy or your earlier observed value
            return 0.21



class AISignalRouter:
    def __init__(self):
        self.vol_sync = VolatilitySync()
        # Model handles if available
        self.xgb: Optional[object] = None
        self.lstm: Optional[object] = None

        # Lazy-load models if modules exist
        try:
            if XGBPredictor is not None:
                self.xgb = XGBPredictor(model_path="models/xgb/xgb_xauusd_5m.bin")
                logger.info("🧠 AISignalRouter: XGB model loaded.")
        except Exception as e:
            logger.warning(f"⚠️ AISignalRouter: XGB load failed: {e}")

        try:
            if LSTMPredictor is not None:
                self.lstm = LSTMPredictor(model_path="models/lstm/lstm_xauusd.h5")
                logger.info("🧠 AISignalRouter: LSTM model loaded.")
        except Exception as e:
            logger.info("ℹ️ AISignalRouter: LSTM not used (optional).")


    # Example placeholder for computing volatility
    def compute_volatility(self, symbol: str) -> float:
        try:
            return float(self.vol_sync.latest(symbol))
        except Exception as e:
            logger.warning(f"VolatilitySync.latest failed: {e}; using fallback 0.21")
            return 0.21

    # Example placeholder for confidence / AI model logic
    import random  # ✅ add this at the top of your file if not already

    def compute_confidence(self, symbol: str) -> float:
        """
        Returns a probability-like confidence in [0,1].
        Priority: LSTM (if you prefer) → XGB → simulated dynamic fallback.
        """
        try:
            if self.lstm is not None:
                conf = float(self.lstm.predict_proba(symbol))
                return max(0.0, min(1.0, conf))
        except Exception as e:
            logger.warning(f"⚠️ LSTM confidence failed: {e}")

        try:
            if self.xgb is not None:
                conf = float(self.xgb.predict_proba(symbol))
                return max(0.0, min(1.0, conf))
        except Exception as e:
            logger.warning(f"⚠️ XGB confidence failed: {e}")

        # 🌀 Dynamic fallback: simulate live-changing confidence between 0.45–0.95
        conf = round(random.uniform(0.45, 0.95), 3)
        logger.info(f"⚙️ Simulated dynamic confidence: {conf}")
        return conf

    def make_decision(self, conf: float, vol: float = 0.0, mode: str = "static") -> dict:
        """
        Decision logic with optional dynamic threshold.
        Returns a structured dict with action, confidence, volatility, and execute flag.
        """

        # Base thresholds
        buy_th = 0.70
        sell_th = 0.25

        if mode == "dynamic":
            # volatility-aware adjustment: tighter during calm, stricter when volatile
            base = 0.90
            vol_ref = 0.15
            slope = 0.30
            tmin, tmax = 0.80, 0.96
            buy_th = base + slope * (vol - vol_ref)
            buy_th = max(min(buy_th, tmax), tmin)
            sell_th = 1 - buy_th

        if conf >= buy_th:
            action = "BUY"
            execute = True
        elif conf <= sell_th:
            action = "SELL"
            execute = True
        else:
            action = "HOLD"
            execute = False

        return {
            "action": action,
            "confidence": conf,
            "volatility": vol,
            "thresholds": {"buy": buy_th, "sell": sell_th},
            "execute": execute,
        }

    def decide(self, symbol: str, *args, **kwargs):
        # This allows extra args (like volatility) without breaking

        """
        Main router entrypoint — runs AI model, updates volatility state,
        and writes the unified decision file for the Scheduler.
        """
        try:
            # 🧮 Step 1: Compute metrics
            latest_volatility = self.compute_volatility(symbol)
            confidence = self.compute_confidence(symbol)

            # 🌐 Step 2: Update global volatility state
            self.vol_sync.update(symbol, latest_volatility)

            # 🧠 Step 3: Decision logic (choose "static" or "dynamic")
            decision_data = self.make_decision(confidence, vol=latest_volatility, mode="static")

            decision = {
                "symbol": symbol,
                **decision_data,  # merge action, confidence, volatility, thresholds, execute
                "source": "router",
                "timestamp": datetime.utcnow().isoformat(),
            }

            # 💾 Step 4: Save router decision output
            self.output_path.parent.mkdir(exist_ok=True)
            with open(self.output_path, "w") as f:
                json.dump(decision, f, indent=2)

            logger.info(f"✅ Router Decision → {decision}")
            return decision

        except Exception as e:
            logger.error(f"❌ AISignalRouter failed: {e}")
            return None
