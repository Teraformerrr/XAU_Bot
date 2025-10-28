import time
import MetaTrader5 as mt5
import logging
from datetime import datetime

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class SmartExecutionEngine:
    """
    Smart Execution Engine (SEE)
    Handles both simulated and live trade placements with safe SL/TP logic,
    auto symbol-fallback (like XAUUSD.sd), and latency tracking.
    """

    def __init__(self):
        logger.info("🧠 SmartExecutionEngine initialized")

    def place_trade(
        self,
        action,
        symbol,
        volume,
        sl_price=None,
        tp_price=None,
        comment="XAU_Bot_Trade",
        magic=5555,
        slippage_pts=50,
        live=True,
    ):
        """
        Places a trade (either simulated or live).
        If live=True, send to MetaTrader5. Otherwise, simulate and log.
        """

        start_time = datetime.now()

        try:
            if not live:
                # Simulated trade for testing
                logger.info(f"🧠 Simulated {action} {symbol} | vol={volume}")
                return {
                    "status": "SIMULATED",
                    "symbol": symbol,
                    "action": action,
                    "price": 0.0,
                    "latency_ms": 0,
                }

            # ✅ Ensure MT5 initialized
            if not mt5.initialize():
                raise RuntimeError("❌ MT5 initialization failed.")

            si = mt5.symbol_info(symbol)

            # If symbol not found, auto-detect
            if not si:
                logger.warning(f"⚠️ {symbol} not found — attempting auto-detect fallback.")
                all_symbols = [s.name for s in mt5.symbols_get() if "XAUUSD" in s.name]
                if all_symbols:
                    symbol = all_symbols[0]
                    logger.warning(f"⚙️ Auto-selected available symbol → {symbol}")
                    mt5.symbol_select(symbol, True)
                    si = mt5.symbol_info(symbol)
                else:
                    raise RuntimeError(f"❌ No matching XAUUSD symbol found in Market Watch.")

            if not si.visible:
                logger.warning(f"⚠️ {symbol} not visible — trying to enable it.")
                if not mt5.symbol_select(symbol, True):
                    raise RuntimeError(f"❌ Failed to select {symbol} in Market Watch.")

            tick = mt5.symbol_info_tick(symbol)
            if not tick:
                raise RuntimeError(f"❌ Failed to get tick for {symbol}")

            # ✅ Price setup
            price = tick.ask if action.upper() == "BUY" else tick.bid
            point = si.point

            # ✅ Dynamic ATR fallback (approximation)
            atr_points = 1200  # you can make this dynamic later
            sl_mult = 1.8
            tp_mult = 3.6

            if action.upper() == "BUY":
                sl_price = sl_price or (price - atr_points * sl_mult * point)
                tp_price = tp_price or (price + atr_points * tp_mult * point)
            else:
                sl_price = sl_price or (price + atr_points * sl_mult * point)
                tp_price = tp_price or (price - atr_points * tp_mult * point)

            fill_mode = getattr(si, "trade_fill_mode", getattr(si, "filling_mode", mt5.ORDER_FILLING_IOC))
            type_filling = mt5.ORDER_FILLING_FOK if (fill_mode & mt5.ORDER_FILLING_FOK) else mt5.ORDER_FILLING_IOC
            deviation_value = int(slippage_pts) if slippage_pts and slippage_pts > 0 else 100

            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": float(volume),
                "type": mt5.ORDER_TYPE_BUY if action.upper() == "BUY" else mt5.ORDER_TYPE_SELL,
                "price": price,
                "sl": round(sl_price, si.digits),
                "tp": round(tp_price, si.digits),
                "deviation": deviation_value,
                "magic": int(magic),
                "comment": comment,
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": type_filling,
            }

            # ✅ Send order
            result = mt5.order_send(request)
            latency_ms = int((datetime.now() - start_time).total_seconds() * 1000)

            if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                logger.info(
                    f"✅ Trade executed successfully: {action} {symbol} @ {result.price:.2f} | SL={sl_price:.2f} | TP={tp_price:.2f}"
                )
                return {
                    "status": "FILLED",
                    "symbol": symbol,
                    "action": action,
                    "price": result.price,
                    "sl": round(sl_price, si.digits),
                    "tp": round(tp_price, si.digits),
                    "latency_ms": latency_ms,
                }
            else:
                last_err = mt5.last_error()
                logger.error(f"❌ Order rejected → {last_err}")
                return {
                    "status": "REJECTED",
                    "symbol": symbol,
                    "action": action,
                    "price": 0.0,
                    "latency_ms": latency_ms,
                    "error": str(last_err),
                }

        except Exception as e:
            logger.exception(f"Trade placement failed: {e}")
            return {"status": "ERROR", "error": str(e), "symbol": symbol}
