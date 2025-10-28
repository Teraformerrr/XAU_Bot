import logging
import MetaTrader5 as mt5

logger = logging.getLogger(__name__)

class ExposureController:
    """
    Smart Exposure Controller (SEC)
    --------------------------------
    - Adjusts requested lots based on confidence, volatility, and equity exposure.
    - Prevents over-leverage and ensures consistent position sizing.
    """

    def __init__(self):
        self.max_symbol_exposure = 2.0     # maximum lots per symbol
        self.max_account_exposure = 10.0   # maximum lots total
        self.min_trade_lot = 0.05          # minimum allowed lot size
        self.equity_risk_limit_pct = 0.02  # 2% risk per trade
        self.scaling_sensitivity = 0.8     # scales with volatility
        logger.info("🧮 Smart Exposure Controller initialized")

    def _get_equity(self):
        acc = mt5.account_info()
        return acc.equity if acc else 100000.0

    def _get_open_exposure(self, symbol):
        positions = mt5.positions_get(symbol=symbol)
        if positions:
            return sum(pos.volume for pos in positions)
        return 0.0

    def evaluate(self, symbol, action, req_lots, confidence, volatility):
        """
        Evaluate exposure for a new trade request.
        Returns scaled or approved lots.
        """

        # 1️⃣ Account and symbol state
        equity = self._get_equity()
        current_exposure = self._get_open_exposure(symbol)

        # 2️⃣ Basic scaling logic
        base_scale = confidence - (volatility * self.scaling_sensitivity)
        scale_factor = max(0.1, min(base_scale, 1.0))  # clamp between 0.1–1.0

        scaled_lot = round(req_lots * scale_factor, 2)

        # 3️⃣ Risk ceiling check (based on equity)
        max_allowed_by_equity = round((equity * self.equity_risk_limit_pct) / 1000, 2)
        # approx. 1 lot per $50k equity = $1000/0.02

        allowed_lot = min(
            scaled_lot,
            self.max_symbol_exposure - current_exposure,
            max_allowed_by_equity,
        )

        # 4️⃣ Enforce minimums
        final_lot = max(allowed_lot, self.min_trade_lot)
        final_lot = round(final_lot, 2)

        # 5️⃣ Logging and classification
        if final_lot < req_lots:
            status = "SCALED"
            logger.warning(f"🟠 SEC | {status} | {symbol} {action} | req={req_lots:.2f} → ok={final_lot:.2f} | conf={confidence:.2f} vol={volatility:.2f}")
        else:
            status = "APPROVED"
            logger.info(f"🟢 SEC | {status} | {symbol} {action} | req={req_lots:.2f} → ok={final_lot:.2f} | conf={confidence:.2f} vol={volatility:.2f}")

        return {"status": status, "approved_lot": final_lot}
