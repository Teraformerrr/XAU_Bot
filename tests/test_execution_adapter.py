# D:\XAU_Bot\tests\test_execution_adapter.py
import logging
from bot.adapters.execution_adapter import ExecutionAdapter

logging.basicConfig(level=logging.INFO)

def test_execution_adapter():
    adapter = ExecutionAdapter(mode="paper", symbol="XAUUSD", lot_size=0.2)

    sample_signals = [
        {"execute": True, "action": "BUY", "confidence": 0.62, "volatility": 0.05},
        {"execute": True, "action": "SELL", "confidence": 0.58, "volatility": 0.12},
        {"execute": False, "action": "HOLD", "confidence": 0.48, "volatility": 0.09},
    ]

    for s in sample_signals:
        result = adapter.execute(s)
        logging.info(f"Adapter Output → {result}")

if __name__ == "__main__":
    test_execution_adapter()
