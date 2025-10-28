import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from bot.scheduler.trade_bridge import TradeBridge


import logging
from bot.scheduler.trade_bridge import TradeBridge

logging.basicConfig(level=logging.INFO)

if __name__ == "__main__":
    bridge = TradeBridge()

    mock_signal = {
        "execute": True,
        "action": "BUY",
        "confidence": 0.63,
        "volatility": 0.08
    }

    result = bridge.process_signal(mock_signal)
    print("TradeBridge Result →", result)
