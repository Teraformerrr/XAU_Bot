"""
policy_bridge.py
Phase 5 – Policy Decision Bridge
Connects AI/Rule-based signal logic with the Scheduler.
"""

import random
from datetime import datetime
from loguru import logger


def get_policy_decision(symbol: str) -> dict:
    """
    Returns a policy decision for the given symbol.
    This is a placeholder AI logic (demo mode).
    """

    # Simulate model confidence and volatility
    confidence = round(random.uniform(0.3, 0.95), 2)
    volatility = round(random.uniform(0.05, 0.4), 2)

    # Demo: occasionally force a trade
    forced = random.random() > 0.65
    execute = forced or confidence > 0.85

    action = "BUY" if random.random() > 0.5 else "SELL"
    reason = "forced-demo" if forced else "demo-idle"

    decision = {
        "symbol": symbol,
        "execute": True,  # force trade
        "action": random.choice(["BUY", "SELL"]),
        "confidence": round(random.uniform(0.8, 0.95), 2),
        "volatility": round(random.uniform(0.1, 0.3), 2),
        "reason": "forced-demo",
        "timestamp": datetime.utcnow().isoformat(),
    }

    logger.debug(f"Policy Bridge Decision → {decision}")
    return decision


# Standalone test
if __name__ == "__main__":
    print(get_policy_decision("XAUUSD"))
