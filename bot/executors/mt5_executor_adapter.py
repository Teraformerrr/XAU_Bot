# D:\XAU_Bot\bot\executors\mt5_executor_adapter.py
from __future__ import annotations
import os, json
from datetime import datetime
from pathlib import Path
from loguru import logger
from dotenv import load_dotenv
import MetaTrader5 as mt5

class MT5ExecutorAdapter:
    def __init__(self):
        load_dotenv()
        self.term_path = os.getenv("MT5_TERMINAL_PATH")
        self.symbol = os.getenv("MT5_SYMBOL", "XAUUSD.sd")
        self.default_lot = float(os.getenv("MT5_LOT", "0.01"))
        self.magic = 987654
        self.initialized = False

    def connect(self):
        if not self.term_path or not Path(self.term_path).exists():
            raise RuntimeError(f"Invalid MT5_TERMINAL_PATH: {self.term_path}")
        if mt5.initialize(path=self.term_path):
            acc = mt5.account_info()
            if acc:
                logger.info(f"✅ Connected to {acc.login} | {acc.server} | balance={acc.balance:.2f}")
                self.initialized = True
                return True
        logger.error(f"MT5 initialization failed: {mt5.last_error()}")
        return False

    def ensure_symbol(self):
        info = mt5.symbol_info(self.symbol)
        if not info:
            raise RuntimeError(f"Symbol not found: {self.symbol}")
        if not info.visible:
            mt5.symbol_select(self.symbol, True)
        return info

    def send_order(self, action: str, lot: float = None, deviation: int = 100, comment: str = "XAU_Bot live exec"):
        if not self.initialized:
            self.connect()
        lot = lot or self.default_lot
        self.ensure_symbol()
        tick = mt5.symbol_info_tick(self.symbol)
        if not tick:
            logger.warning("No tick data available — possibly market closed.")
            return {"status": "market_closed"}

        order_type = mt5.ORDER_TYPE_BUY if action.upper() == "BUY" else mt5.ORDER_TYPE_SELL
        price = tick.ask if order_type == mt5.ORDER_TYPE_BUY else tick.bid

        # ── Auto TP/SL Calculation ─────────────────────────────────────
        atr_pips = 3.0  # Example ATR-like offset (you can later link it to actual ATR)
        sl_distance = atr_pips * 2  # Stop Loss = 2 × ATR
        tp_distance = atr_pips * 3  # Take Profit = 3 × ATR

        if order_type == mt5.ORDER_TYPE_BUY:
            sl = price - sl_distance
            tp = price + tp_distance
        else:
            sl = price + sl_distance
            tp = price - tp_distance

        # ── Trade Request with SL/TP ────────────────────────────────────
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": self.symbol,
            "volume": float(lot),
            "type": order_type,
            "price": price,
            "deviation": deviation,
            "sl": round(sl, 2),
            "tp": round(tp, 2),
            "magic": self.magic,
            "comment": comment,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        result = mt5.order_send(request)
        if result and result.retcode in (mt5.TRADE_RETCODE_DONE, mt5.TRADE_RETCODE_PLACED):
            logger.success(f"✅ Order executed → {action} {self.symbol} {lot} @ {price}")
            self._log_trade(action, lot, price, result)
            return {"status": "success", "retcode": result.retcode, "deal": result.deal}
        else:
            comment_out = result.comment if result else "Unknown error"
            logger.warning(f"⚠️ Trade rejected: {comment_out}")
            return {"status": "failed", "retcode": getattr(result, 'retcode', None), "comment": comment_out}

    def modify_position_sl_tp(self, ticket: int, sl: float = None, tp: float = None) -> bool:
        """
        Modify SL/TP for an existing position using TRADE_ACTION_SLTP.
        """
        position = next((p for p in (mt5.positions_get() or []) if p.ticket == ticket), None)
        if not position:
            return False

        price = mt5.symbol_info_tick(position.symbol).bid if position.type == mt5.POSITION_TYPE_BUY \
                else mt5.symbol_info_tick(position.symbol).ask

        req = {
            "action": mt5.TRADE_ACTION_SLTP,
            "symbol": position.symbol,
            "position": ticket,
            "sl": float(sl) if sl else position.sl,
            "tp": float(tp) if tp else position.tp,
            "price": price,
            "magic": self.magic,
            "comment": "XAU_Bot SLTP modify",
        }
        res = mt5.order_send(req)
        ok = bool(res and res.retcode in (mt5.TRADE_RETCODE_DONE, mt5.TRADE_RETCODE_PLACED))
        if ok:
            logger.info(f"✏️  SL/TP modified | ticket={ticket} | SL={req['sl']:.2f} TP={req['tp']:.2f}")
        else:
            logger.warning(f"SL/TP modify rejected | ticket={ticket} | retcode={getattr(res,'retcode',None)}")
        return ok

    def close_position(self, ticket: int, deviation: int = 150) -> bool:
        """
        Close a specific position by sending an opposite market order.
        """
        position = next((p for p in (mt5.positions_get() or []) if p.ticket == ticket), None)
        if not position:
            return False

        tick = mt5.symbol_info_tick(position.symbol)
        if not tick:
            return False

        order_type = mt5.ORDER_TYPE_SELL if position.type == mt5.POSITION_TYPE_BUY else mt5.ORDER_TYPE_BUY
        price = tick.bid if order_type == mt5.ORDER_TYPE_SELL else tick.ask

        req = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": position.symbol,
            "volume": position.volume,
            "type": order_type,
            "position": ticket,
            "price": price,
            "deviation": deviation,
            "magic": self.magic,
            "comment": "XAU_Bot close",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        res = mt5.order_send(req)
        ok = bool(res and res.retcode in (mt5.TRADE_RETCODE_DONE, mt5.TRADE_RETCODE_PLACED))
        if ok:
            logger.info(f"✅ Closed position ticket={ticket} | retcode={res.retcode}")
        else:
            logger.warning(f"Close rejected | ticket={ticket} | retcode={getattr(res,'retcode',None)} | {getattr(res,'comment', '')}")
        return ok

    # ── internal log ────────────────────────────────────────────────────────
    def _log_trade(self, action, lot, price, result):
        payload = {
            "timestamp": datetime.utcnow().isoformat(timespec="seconds"),
            "symbol": self.symbol,
            "action": action,
            "lot": lot,
            "price": price,
            "deal": getattr(result, "deal", None),
            "order": getattr(result, "order", None),
            "retcode": result.retcode,
            "comment": result.comment,
            "status": "EXECUTED",
        }
        log_path = Path("reports/live_trade_log.jsonl")
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload) + "\n")

    def shutdown(self):
        mt5.shutdown()
        logger.info("🔌 MT5 connection closed.")
