import time
import logging
from datetime import datetime
from ..execution.execution_adapter import ExecutionAdapter
from ..portfolio.trade_logger import TradeLogger
from ..portfolio.portfolio_state import PortfolioState


logger = logging.getLogger(__name__)

class TradeBridge:
    def __init__(self, adapter=None, logger_cls=None):
        self.adapter = adapter or ExecutionAdapter()
        self.trade_logger = logger_cls or TradeLogger()
        self.portfolio_state = PortfolioState()

    def process_signal(self, signal: dict):
        """
        Accepts a trading signal from BayesianPolicyBridge or LSTM module.
        Expected format:
            {'execute': True, 'action': 'BUY', 'confidence': 0.62, 'volatility': 0.05}
        """
        if not signal.get("execute"):
            logger.info("🚫 No trade execution triggered (execute=False)")
            return {"status": "skipped", "reason": "no execution flag"}

        action = signal.get("action")
        conf = signal.get("confidence")
        vol = signal.get("volatility", 0)

        # Basic sanity checks
        if action not in ["BUY", "SELL"]:
            logger.warning(f"⚠️ Invalid action: {action}")
            return {"status": "error", "reason": "invalid action"}

        if conf < 0.55:
            logger.info(f"🟡 Confidence too low ({conf:.2f}), skipping trade.")
            return {"status": "skipped", "reason": "low confidence"}

        # Portfolio and risk checks
        portfolio = self.portfolio_state.load()
        open_positions = portfolio.get("total_trades", 0)
        equity = portfolio.get("equity", 10000)

        if open_positions >= 3:
            logger.info("⏸ Too many open positions, skipping.")
            return {"status": "skipped", "reason": "max positions"}

        # Execute simulated trade
        result = self.adapter.execute_trade(
            symbol="XAUUSD",
            action=action,
            confidence=conf,
            volatility=vol
        )

        # Log trade
        trade_log = self.trade_logger.log_trade(result)
        logger.info(f"✅ Trade executed & logged | {action} @ conf={conf:.2f}")

        return {"status": "executed", "trade": trade_log}
