from bot.reports.cycle_reporter import CycleReporter
from datetime import datetime

def test_cycle_reporter():
    reporter = CycleReporter()
    mock_data = {
        "cycle_id": 1,
        "timestamp": datetime.utcnow().isoformat(),
        "equity": 100500.25,
        "realized_pnl": 250.5,
        "unrealized_pnl": -50.25,
        "trades": [
            {"symbol": "XAUUSD", "action": "BUY", "pnl": 125.75},
            {"symbol": "XAUUSD", "action": "SELL", "pnl": -50.25}
        ],
        "signals": {"buy_conf": 0.61, "sell_conf": 0.48},
        "regime": "trend"
    }

    summary = reporter.summarize_cycle(mock_data)
    assert "cycle_id" in summary
    assert summary["trade_count"] == 2
    print(summary)

if __name__ == "__main__":
    test_cycle_reporter()
