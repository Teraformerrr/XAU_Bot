import MetaTrader5 as mt5
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class PositionManager:
    """
    Handles open position logic, TP/SL management, and equity synchronization.
    """
    def __init__(self, adapter, symbol: str, cfg=None):
        self.adapter = adapter
        self.symbol = symbol
        self.cfg = cfg
        self._connect_mt5()

    # ------------------------
    def _connect_mt5(self):
        if not mt5.initialize():
            raise RuntimeError("❌ MT5 initialization failed.")
        acc_info = mt5.account_info()
        if acc_info:
            logger.info(f"✅ Connected to {acc_info.login} | Balance={acc_info.balance}")
        else:
            logger.warning("⚠️ Could not fetch MT5 account info.")

    # ------------------------
    def get_live_equity(self) -> float:
        acc = mt5.account_info()
        return round(acc.equity, 2) if acc else 0.0

    # ------------------------
    def get_open_positions(self, symbol=None):
        if symbol:
            return [p for p in mt5.positions_get(symbol=symbol) or []]
        return mt5.positions_get() or []

    # ------------------------
    def close_all(self, symbol=None):
        positions = self.get_open_positions(symbol)
        for pos in positions:
            lot = pos.volume
            order_type = mt5.ORDER_SELL if pos.type == 0 else mt5.ORDER_BUY
            mt5.order_send({
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": pos.symbol,
                "volume": lot,
                "type": order_type,
                "position": pos.ticket,
                "deviation": 20,
                "comment": "Auto-close",
            })
            logger.info(f"🔻 Closed {pos.symbol} {lot} lot(s) (ticket={pos.ticket})")

    # ------------------------
    def open_trade(self, action: str, lots: float, atr_price: float = 3.0):
        """
        Opens trade with dynamic SL/TP using ATR multiples.
        """
        symbol_info = mt5.symbol_info(self.symbol)
        if not symbol_info:
            raise RuntimeError(f"Symbol {self.symbol} not found in MT5.")

        tick = mt5.symbol_info_tick(self.symbol)
        if not tick:
            raise RuntimeError(f"❌ Failed to get latest tick for {self.symbol}.")

        price = tick.ask if action == "BUY" else tick.bid
        point = symbol_info.point

        sl = None
        tp = None
        # Dynamic SL/TP: 1.5x ATR for SL, 2.5x ATR for TP
        if atr_price:
            if action == "BUY":
                sl = round(price - atr_price * 1.5, 2)
                tp = round(price + atr_price * 2.5, 2)
            else:
                sl = round(price + atr_price * 1.5, 2)
                tp = round(price - atr_price * 2.5, 2)

        order_type = mt5.ORDER_BUY if action == "BUY" else mt5.ORDER_SELL
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": self.symbol,
            "volume": lots,
            "type": order_type,
            "price": price,
            "sl": sl,
            "tp": tp,
            "deviation": 50,
            "comment": f"{action} by bot",
            "type_filling": mt5.ORDER_FILLING_IOC,
            "type_time": mt5.ORDER_TIME_GTC,
        }

        result = mt5.order_send(request)
        if result and result.retcode == mt5.TRADE_RETCODE_DONE:
            logger.success(f"✅ Order executed → {action} {self.symbol} {lots} @ {price} | SL={sl} | TP={tp}")
        else:
            logger.error(f"❌ Trade failed: {result}")

        return result

    # ------------------------
    def maintain(self, action: str, atr_price: float = 3.0):
        """
        Ensures only one open position per symbol. If direction flips → close opposite first.
        """
        open_positions = self.get_open_positions(self.symbol)
        if not open_positions:
            return None  # No open trades

        pos = open_positions[0]
        current_type = "BUY" if pos.type == 0 else "SELL"
        if current_type != action:
            logger.warning(f"⚠️ Bias flipped ({current_type} → {action}), closing old and reopening.")
            self.close_all(self.symbol)
            self.open_trade(action, pos.volume, atr_price)
