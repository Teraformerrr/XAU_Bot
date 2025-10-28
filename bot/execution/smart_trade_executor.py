import MetaTrader5 as mt5
import json, time, os
from datetime import datetime
from loguru import logger


class SmartTradeExecutor:
    """
    Handles trade validation, cooldown, duplicate prevention and live logging.
    """
    def __init__(self, cooldown_sec=300, log_path="runtime/trade_log.json"):
        self.cooldown_sec = cooldown_sec
        self.last_trade_time = {}
        self.log_path = log_path
        os.makedirs(os.path.dirname(log_path), exist_ok=True)

    # -------------------------------------------------------------------------
    def can_trade(self, symbol):
        """Return False if cooldown active or existing open trade detected."""
        now = time.time()
        if symbol in self.last_trade_time:
            elapsed = now - self.last_trade_time[symbol]
            if elapsed < self.cooldown_sec:
                logger.warning(f"⏸️ Cooldown active for {symbol} ({elapsed:.1f}s/{self.cooldown_sec}s)")
                return False

        # Check open positions
        positions = mt5.positions_get(symbol=symbol)
        if positions:
            logger.warning(f"⚠️ {symbol} already has open positions — skipping new trade.")
            return False
        return True

    # -------------------------------------------------------------------------
    def record_trade(self, symbol, action, volume, price, result):
        """Log every trade with timestamp and status to runtime JSON."""
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "symbol": symbol,
            "action": action,
            "volume": volume,
            "price": price,
            "result": result,
        }
        data = []
        if os.path.exists(self.log_path):
            try:
                with open(self.log_path, "r") as f:
                    data = [json.loads(line) for line in f if line.strip()]
            except Exception:
                data = []
        data.append(entry)
        with open(self.log_path, "w") as f:
            for d in data:
                f.write(json.dumps(d) + "\n")
        logger.info(f"🧾 Trade logged → {symbol} {action} {volume}@{price}")

    # -------------------------------------------------------------------------
    def update_cooldown(self, symbol):
        """Mark symbol as recently traded."""
        self.last_trade_time[symbol] = time.time()
        logger.debug(f"⏱️ Cooldown timer reset for {symbol}")

