# D:\XAU_Bot\bot\executors\trade_feedback_monitor.py
from __future__ import annotations
import MetaTrader5 as mt5
from datetime import datetime, timedelta
from loguru import logger
from bot.engines.adaptive_feedback import AdaptiveFeedback

class TradeFeedbackMonitor:
    """
    Polls MT5 closed deals and pushes outcomes into AdaptiveFeedback.
    Maintains last-check timestamp to avoid duplicates.
    """
    def __init__(self, feedback_engine: AdaptiveFeedback, symbol: str):
        self.feedback_engine = feedback_engine
        self.symbol = symbol
        self.last_check = datetime.utcnow() - timedelta(minutes=5)

    def poll_closed_trades(self):
        now = datetime.utcnow()
        # fetch recent history since last check
        deals = mt5.history_deals_get(self.last_check, now)
        self.last_check = now
        if not deals:
            return

        for d in deals:
            if getattr(d, "symbol", "") != self.symbol:
                continue
            profit = float(getattr(d, "profit", 0.0))
            comment = getattr(d, "comment", "")
            conf_hint = 0.5
            if "conf=" in comment:
                try:
                    conf_hint = float(comment.split("conf=")[-1])
                except Exception:
                    pass
            win_flag = profit > 0
            self.feedback_engine.update(self.symbol, win_flag, conf_hint)
            logger.info(f"📊 Feedback updated from real trade | {self.symbol} | profit={profit:.2f} | win={win_flag}")
