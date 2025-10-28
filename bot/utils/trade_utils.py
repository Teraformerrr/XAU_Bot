import random
from datetime import datetime

def simulate_trade(symbol: str, action: str, lots: float, confidence: float):
    """
    Simulates a paper-mode trade.
    Generates a pseudo price and PnL outcome for logging & backtest visualization.
    """

    # Generate a random fake execution price within a plausible range
    price = round(random.uniform(2375, 2395), 2)

    # Simulate PnL using confidence and direction
    base_pnl = random.uniform(-80, 150)
    weighted_pnl = base_pnl * (confidence + 0.2)  # higher confidence → more likely profit
    pnl = round(weighted_pnl, 2)

    timestamp = datetime.utcnow().isoformat()

    return {
        "timestamp": timestamp,
        "symbol": symbol,
        "action": action,
        "lots": lots,
        "price": price,
        "pnl": pnl,
        "status": "SIMULATED",
    }
