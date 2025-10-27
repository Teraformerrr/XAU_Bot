# D:\XAU_Bot\bot\adapters\execution_adapter.py
import logging
from datetime import datetime
from typing import Dict

try:
    import MetaTrader5 as mt5
except ImportError:
    mt5 = None

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-8s | %(message)s")


class ExecutionAdapter:
    """
    Translates policy actions into executable MT5 orders or simulated actions.
    """

    def __init__(self, mode: str = "paper", symbol: str = "XAUUSD", lot_size: float = 0.1):
        self.mode = mode
        self.symbol = symbol
        self.lot_size = lot_size
        self.connected = False

        if mt5:
            self.connected = mt5.initialize()
            if not self.connected:
                logger.warning("⚠️ MT5 connection failed — using simulation mode.")
        else:
            logger.warning("⚠️ MetaTrader5 module not available — using simulation mode.")

    # ------------------------------------------------------------

    def execute(self, policy_output: Dict) -> Dict:
        """
        Executes a trade or simulation based on the policy output.
        Expected keys: {'execute': bool, 'action': 'BUY'|'SELL'|'HOLD', ...}
        """
        ts = datetime.utcnow().isoformat()

        if not policy_output.get("execute"):
            return {"status": "SKIPPED", "action": "HOLD", "timestamp": ts}

        action = policy_output.get("action")
        confidence = policy_output.get("confidence")
        vol = policy_output.get("volatility")

        if self.mode == "live" and self.connected:
            # --- Live execution ---
            order_type = mt5.ORDER_BUY if action == "BUY" else mt5.ORDER_SELL
            result = mt5.order_send({
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": self.symbol,
                "volume": self.lot_size,
                "type": order_type,
                "price": mt5.symbol_info_tick(self.symbol).ask if action == "BUY" else mt5.symbol_info_tick(self.symbol).bid,
                "deviation": 10,
                "magic": 777,
                "comment": "XAU_Bot auto execution",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            })

            if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                logger.info(f"✅ Live trade executed: {action} {self.symbol} {self.lot_size}")
                status = "EXECUTED"
            else:
                logger.error(f"❌ Trade failed: {getattr(result, 'retcode', 'Unknown')}")
                status = "FAILED"
        else:
            # --- Paper/simulated execution ---
            logger.info(f"🧠 Simulated {action} {self.symbol} | conf={confidence:.2f} | vol={vol:.2f}")
            status = "SIMULATED"

        return {
            "status": status,
            "symbol": self.symbol,
            "action": action,
            "confidence": confidence,
            "volatility": vol,
            "timestamp": ts,
        }
