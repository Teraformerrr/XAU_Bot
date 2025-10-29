# D:\XAU_Bot\bot\executors\smart_trade_executor.py
from __future__ import annotations
import os
from dataclasses import dataclass
from typing import Optional, Dict, Any
from loguru import logger
from dotenv import load_dotenv

# Live adapter we built in the last step
from .mt5_executor_adapter import MT5ExecutorAdapter

# ── Optional gates: DRG / SEC ──────────────────────────────────────────────
# We try to import your existing governors. If not available, we allow trade.
def _try_import_drg():
    try:
        # expected user module (adjust if your path differs)
        from bot.risk.dynamic_governor import DynamicRiskGovernor  # type: ignore
        return DynamicRiskGovernor()
    except Exception:
        logger.warning("DRG not found → allowing by default.")
        return None

def _try_import_sec():
    try:
        # expected user module (adjust if your path differs)
        from bot.risk.smart_exposure import SmartExposureController  # type: ignore
        return SmartExposureController()
    except Exception:
        logger.warning("SEC not found → basic lot checks only.")
        return None
# ───────────────────────────────────────────────────────────────────────────


@dataclass
class ExecContext:
    action: str
    confidence: float
    volatility: float
    lot: Optional[float] = None
    meta: Optional[Dict[str, Any]] = None


class SmartTradeExecutor:
    """
    Bridges Scheduler/AI signals → MT5 live orders via MT5ExecutorAdapter.
    Honors EXECUTION_MODE=live|paper and optional DRG/SEC gates if present.
    """
    def __init__(self):
        load_dotenv()
        self.mode = os.getenv("EXECUTION_MODE", "live").lower()  # live | paper
        self.symbol = os.getenv("MT5_SYMBOL", "XAUUSD.sd")
        self.default_lot = float(os.getenv("MT5_LOT", "0.01"))

        self.adapter = MT5ExecutorAdapter()
        self._drg = _try_import_drg()
        self._sec = _try_import_sec()
        self._connected = False

    # ── Helpers ─────────────────────────────────────────────────────────────
    def _connect_once(self):
        if not self._connected:
            ok = self.adapter.connect()
            self._connected = bool(ok)

    def _market_open(self) -> bool:
        # tick presence is the most reliable runtime check
        try:
            import MetaTrader5 as mt5
            self.adapter.ensure_symbol()
            tick = mt5.symbol_info_tick(self.symbol)
            return bool(tick and (tick.bid or tick.ask))
        except Exception:
            return False

    def _lot_from_policy(self, lot_hint: Optional[float]) -> float:
        lot = lot_hint if lot_hint and lot_hint > 0 else self.default_lot
        # basic min clamp; SEC (if available) will enforce stricter rules
        if lot < 0.01:
            lot = 0.01
        return round(float(lot), 2)
    # ────────────────────────────────────────────────────────────────────────

    def execute(self, ctx: ExecContext) -> Dict[str, Any]:
        """
        Main entry from Scheduler.
        ctx.action: 'BUY' or 'SELL'
        """
        self._connect_once()

        if not self._market_open():
            logger.warning("⏸️ Market closed — skipping order.")
            return {"status": "market_closed"}

        # DRG gate (if present)
        if self._drg:
            try:
                allowed = self._drg.allows(confidence=ctx.confidence, volatility=ctx.volatility)  # type: ignore
                if not allowed:
                    logger.warning("🛑 DRG blocked execution.")
                    return {"status": "blocked_drg"}
            except Exception as e:
                logger.error(f"DRG error → allowing by default: {e}")

        # Lot sizing
        lot = self._lot_from_policy(ctx.lot)

        # SEC validation (if present)
        if self._sec:
            try:
                ok, adj_lot = self._sec.validate(symbol=self.symbol, lot=lot, confidence=ctx.confidence, volatility=ctx.volatility)  # type: ignore
                if not ok:
                    logger.warning("🛑 SEC rejected order.")
                    return {"status": "blocked_sec"}
                if adj_lot and adj_lot != lot:
                    logger.info(f"🔧 SEC adjusted lot {lot} → {adj_lot}")
                    lot = adj_lot
            except Exception as e:
                logger.error(f"SEC error → continuing with lot={lot}: {e}")

        if self.mode != "live":
            logger.info(f"🧪 PAPER MODE → {ctx.action} {self.symbol} {lot} (no real order sent)")
            return {"status": "paper", "action": ctx.action, "lot": lot}

        # Live execution
        comment = f"XAU_Bot live exec conf={ctx.confidence:.3f}"
        result = self.adapter.send_order(ctx.action, lot=lot, comment=comment)
        return result
