import json
from datetime import datetime
from loguru import logger
from pathlib import Path


def log_trade(symbol, action, confidence, volatility, volume, price, pnl, status, portfolio_state):
    """
    Logs a trade entry and updates portfolio.json with the latest portfolio + trade history.
    """
    trade = {
        "symbol": symbol,
        "action": action,
        "confidence": confidence,
        "volatility": volatility,
        "volume": volume,
        "price": price,
        "pnl": pnl,
        "status": status,
        "timestamp": datetime.utcnow().isoformat()
    }

    portfolio = {
        "equity": portfolio_state.get("equity", 0),
        "realized_pnl": portfolio_state.get("realized_pnl", 0),
        "unrealized_pnl": portfolio_state.get("unrealized_pnl", 0),
        "win_trades": portfolio_state.get("win_trades", 0),
        "loss_trades": portfolio_state.get("loss_trades", 0),
        "total_trades": portfolio_state.get("total_trades", 0),
        "last_update": datetime.utcnow().isoformat()
    }

    output = {
        "status": "logged",
        "trade": trade,
        "portfolio": portfolio
    }

    # Write to JSON file safely
    portfolio_file = Path("portfolio.json")
    try:
        if portfolio_file.exists():
            with open(portfolio_file, "r") as f:
                existing = json.load(f)
        else:
            existing = {"portfolio": portfolio, "trades": []}

        existing["portfolio"] = portfolio
        existing.setdefault("trades", []).append(trade)

        with open(portfolio_file, "w") as f:
            json.dump(existing, f, indent=2)

        logger.info(f"💾 portfolio.json updated successfully | {len(existing['trades'])} trades logged.")

    except Exception as e:
        logger.error(f"❌ Failed to save portfolio.json: {e}")

    logger.info(f"📘 Trade logged | {symbol} {action} | PnL={pnl} | Equity={portfolio['equity']}")
    return output
