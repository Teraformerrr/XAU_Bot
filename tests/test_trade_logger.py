from bot.portfolio.trade_logger import log_trade

if __name__ == "__main__":
    # Simulate portfolio state (this would normally come from live updates)
    portfolio_state = {
        "equity": 100000.0 + 125.75,
        "realized_pnl": 125.75 * 2,
        "unrealized_pnl": 0.0,
        "win_trades": 2,
        "loss_trades": 0,
        "total_trades": 2
    }

    # Log one simulated trade
    result = log_trade(
        symbol="XAUUSD",
        action="BUY",
        confidence=0.61,
        volatility=0.08,
        volume=1.0,
        price=2385.2,
        pnl=125.75,
        status="SIMULATED",
        portfolio_state=portfolio_state
    )

    print(result)
