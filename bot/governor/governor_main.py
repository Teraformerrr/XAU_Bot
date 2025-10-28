# D:\XAU_Bot\bot\governor\governor_main.py
from __future__ import annotations
from typing import Dict, Any
from bot.governor.exposure_controller import SmartExposureController, SECConfig

# Initialize once and reuse
_sec = SmartExposureController(SECConfig())

def gate_exposure(order: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validates exposure before trade execution.

    Input Example:
    order = {
        "symbol": "XAUUSD",
        "action": "BUY" | "SELL",
        "lots": 2.0,
        "confidence": 0.62,
        "volatility": 0.18
    }

    Returns:
        {
          "execute": bool,
          "lots": float,
          "status": "APPROVED|SCALED|DENIED",
          "sec": <full sec decision dict>
        }
    """
    symbol = order["symbol"]
    lots = float(order["lots"])
    action = order["action"]
    conf = float(order.get("confidence", 0.5))
    vol = float(order.get("volatility", 0.2))

    sec_decision = _sec.decide(symbol, lots, conf, vol, action)
    status = sec_decision["status"]

    if status == "APPROVED":
        return {"execute": True, "lots": lots, "status": status, "sec": sec_decision}
    if status == "SCALED" and sec_decision["approved_lots"] > 0.0:
        return {
            "execute": True,
            "lots": sec_decision["approved_lots"],
            "status": status,
            "sec": sec_decision
        }
    return {"execute": False, "lots": 0.0, "status": status, "sec": sec_decision}
