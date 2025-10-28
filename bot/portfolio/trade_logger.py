import json
import os
from datetime import datetime
from loguru import logger

class TradeLogger:
    """
    Handles trade logging for each executed trade.
    Supports logging trades to a JSON file and feeding portfolio metrics.
    """

    def __init__(self, log_path="reports/trades/trade_log.json"):
        self.log_path = log_path
        os.makedirs(os.path.dirname(self.log_path), exist_ok=True)

    def log_trade(self, symbol: str, action: str, pnl: float = 0.0, equity: float = 0.0):
        """
        Logs a trade event.

        Args:
            symbol (str): Instrument traded, e.g., 'XAUUSD'
            action (str): Trade direction ('BUY' or 'SELL')
            pnl (float): Profit or loss of the trade
            equity (float): Current account equity
        """
        trade = {
            "symbol": symbol,
            "action": action,
            "pnl": pnl,
            "equity": equity,
            "timestamp": datetime.utcnow().isoformat(),
            "status": "SIMULATED"
        }

        # Load existing log
        if os.path.exists(self.log_path):
            try:
                with open(self.log_path, "r") as f:
                    trades = json.load(f)
            except json.JSONDecodeError:
                trades = []
        else:
            trades = []

        # Append new trade
        trades.append(trade)
        with open(self.log_path, "w") as f:
            json.dump(trades, f, indent=4)

        logger.info(f"📘 Trade logged | {symbol} {action} | PnL={pnl} | Equity={equity}")
        return {"status": "logged", "trade": trade}
