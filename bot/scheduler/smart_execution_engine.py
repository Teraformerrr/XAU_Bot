import logging
from datetime import datetime
from bot.utils.mt5_connector import MT5Connector
from bot.utils.trade_utils import simulate_trade

logger = logging.getLogger(__name__)

class SmartExecutionEngine:
    """
    Phase 5.4 – Smart Trade Executor (STE)
    Handles trade execution routing (real vs paper mode) and logging.
    """

    def __init__(self, config):
        self.config = config
        self.mode = config.get("mode", "paper")
        self.mt5 = MT5Connector(config) if self.mode == "live" else None
        logger.info("🧠 SmartExecutionEngine initialized | Mode=%s", self.mode)

    def execute_trade(self, symbol: str, action: str, confidence: float, volatility: float):
        """
        Executes a trade based on mode and logs the result.
        """
        timestamp = datetime.utcnow().isoformat()
        lots = self._calc_lots(confidence, volatility)
        trade_data = {
            "timestamp": timestamp,
            "symbol": symbol,
            "action": action,
            "lots": lots,
            "confidence": confidence,
            "volatility": volatility,
        }

        try:
            if self.mode == "live":
                # Send to MetaTrader 5
                result = self.mt5.place_order(symbol, action, lots)
                trade_data.update(result)
                logger.info("✅ Live trade executed → %s %.2f lots @ %s",
                            action, lots, result.get("price"))
            else:
                # Paper-mode simulation
                sim_result = simulate_trade(symbol, action, lots, confidence)
                trade_data.update(sim_result)
                logger.info("🧪 Simulated %s trade | PnL=%.2f | Price=%.2f",
                            action, sim_result["pnl"], sim_result["price"])

            return trade_data

        except Exception as e:
            logger.error("❌ Trade execution error: %s", e)
            trade_data["status"] = "error"
            trade_data["error"] = str(e)
            return trade_data

    # ------------------------------------------------------------------
    def _calc_lots(self, confidence: float, volatility: float) -> float:
        """
        Simple dynamic-lot calculator based on confidence & volatility.
        """
        base = 0.10
        adj = round(base * (confidence / max(volatility, 0.01)), 2)
        return min(max(adj, 0.01), 5.00)
