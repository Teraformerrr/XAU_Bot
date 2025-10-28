import logging
import random
from datetime import datetime

logger = logging.getLogger(__name__)

class MT5Connector:
    """
    Lightweight MetaTrader 5 connector.
    Works in two modes:
    - live: real trade execution using MetaTrader5 library
    - paper: simulated trades (fallback)
    """

    def __init__(self, config):
        self.config = config
        self.connected = False
        self.mode = config.get("mode", "paper")
        self.account = None

        try:
            if self.mode == "live":
                import MetaTrader5 as mt5
                if not mt5.initialize():
                    raise ConnectionError("MT5 initialization failed.")
                self.connected = True
                self.account = mt5.account_info().login
                logger.info("✅ MT5 Connected | Account: %s", self.account)
            else:
                logger.info("💡 MT5Connector initialized in paper mode (no live connection)")
        except Exception as e:
            logger.error("❌ MT5 connection failed: %s", e)
            self.connected = False

    # ------------------------------------------------------------------
    def place_order(self, symbol: str, action: str, lots: float):
        """
        Execute a live order on MT5 or simulate in paper mode.
        Returns a dict with trade result.
        """
        timestamp = datetime.utcnow().isoformat()
        fake_price = round(random.uniform(2370, 2400), 2)

        if self.mode != "live":
            # Paper/simulated
            pnl = round(random.uniform(-50, 150), 2)
            logger.info("🧪 Simulated %s trade | %s | %.2f lots | PnL=%.2f",
                        symbol, action, lots, pnl)
            return {
                "symbol": symbol,
                "action": action,
                "lots": lots,
                "price": fake_price,
                "pnl": pnl,
                "status": "SIMULATED",
                "timestamp": timestamp,
            }

        try:
            import MetaTrader5 as mt5
            order_type = mt5.ORDER_TYPE_BUY if action.upper() == "BUY" else mt5.ORDER_TYPE_SELL
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": lots,
                "type": order_type,
                "price": mt5.symbol_info_tick(symbol).ask if order_type == mt5.ORDER_TYPE_BUY else mt5.symbol_info_tick(symbol).bid,
                "deviation": 10,
                "magic": 123456,
                "comment": "XAU_Bot auto-trade",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }

            result = mt5.order_send(request)
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                raise RuntimeError(f"MT5 order failed: {result.comment}")

            logger.info("✅ Live order executed: %s %.2f lots @ %.2f", action, lots, request["price"])
            return {
                "symbol": symbol,
                "action": action,
                "lots": lots,
                "price": request["price"],
                "status": "EXECUTED",
                "timestamp": timestamp,
            }


        except Exception as e:
            logger.error("❌ Live order execution error: %s", e)
            return {
                "symbol": symbol,
                "action": action,
                "lots": lots,
                "status": "ERROR",
                "error": str(e),
                "timestamp": timestamp,
            }
