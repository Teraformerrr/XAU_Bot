import logging
from typing import Optional, Dict

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")

class LiveExecutor:
    """
    Thin wrapper around your existing execution adapter.
    - In 'paper' mode → returns a SIMULATED order dict.
    - In 'live'  mode → tries to use your adapter; if import fails, falls back to SIMULATED.
    """
    def __init__(self, mode: str = "paper"):
        self.mode = mode.lower().strip()
        self._adapter = None

        if self.mode == "live":
            try:
                # Adjust this import if your adapter path differs
                from bot.adapters.execution_adapter import ExecutionAdapter
                self._adapter = ExecutionAdapter()
                logging.info("✅ LiveExecutor: MT5 adapter loaded.")
            except Exception as e:
                logging.warning(f"⚠️ LiveExecutor: MT5 adapter not available ({e}). Falling back to SIMULATED.")
                self.mode = "paper"

    def send_order(
        self,
        symbol: str,
        action: str,
        volume: float,
        sl: Optional[float] = None,
        tp: Optional[float] = None,
        price: Optional[float] = None,
        comment: str = "XAU_Bot LSTM-Fused"
    ) -> Dict:
        action = action.upper()
        if self.mode == "paper" or self._adapter is None:
            out = {
                "status": "SIMULATED",
                "symbol": symbol,
                "action": action,
                "volume": volume,
                "price": price,
                "sl": sl,
                "tp": tp,
                "comment": comment,
            }
            logging.info(f"🧠 Simulated {action} {symbol} | vol={volume} | sl={sl} | tp={tp}")
            return out

        # Live path through your adapter (adjust call signature if needed)
        try:
            result = self._adapter.place_order(symbol=symbol, action=action, volume=volume, sl=sl, tp=tp, price=price, comment=comment)
            logging.info(f"🟢 LIVE {action} {symbol} → {result}")
            return result
        except Exception as e:
            logging.error(f"❌ Live order failed ({e}). Returning SIMULATED output.")
            return {
                "status": "SIMULATED",
                "symbol": symbol,
                "action": action,
                "volume": volume,
                "price": price,
                "sl": sl,
                "tp": tp,
                "comment": f"{comment} | live-fallback: {e}",
            }
