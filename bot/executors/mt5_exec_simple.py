from loguru import logger
import os
import time
import json
from datetime import datetime
from pathlib import Path

import MetaTrader5 as mt5
from dotenv import load_dotenv

def _env(name, default=None, cast=str):
    v = os.getenv(name, default)
    return cast(v) if (v is not None and cast is not str) else v

def initialize_mt5():
    load_dotenv()
    term_path = _env("MT5_TERMINAL_PATH")
    login     = os.getenv("MT5_LOGIN")
    password  = os.getenv("MT5_PASSWORD")
    server    = os.getenv("MT5_SERVER")

    if not term_path or not Path(term_path).exists():
        raise RuntimeError(f"MT5_TERMINAL_PATH invalid or missing: {term_path}")

    # Prefer initializing with explicit login if provided; otherwise reuse current terminal session.
    if login and password and server:
        login = int(login)
        ok = mt5.initialize(path=term_path, login=login, password=password, server=server)
    else:
        ok = mt5.initialize(path=term_path)

    if not ok:
        raise RuntimeError(f"mt5.initialize failed: {mt5.last_error()}")

    logger.info("✅ MT5 initialized.")
    acc = mt5.account_info()
    if acc is None:
        raise RuntimeError("No account_info() — is terminal logged in?")
    logger.info(f"👤 Account: {acc.login} | {acc.server} | leverage {acc.leverage} | balance {acc.balance:.2f}")
    return True

def ensure_symbol(symbol):
    info = mt5.symbol_info(symbol)
    if info is None:
        raise RuntimeError(f"Symbol not found: {symbol} (check broker suffix)")
    if not info.visible:
        if not mt5.symbol_select(symbol, True):
            raise RuntimeError(f"Unable to show symbol in Market Watch: {symbol}")
    logger.info(f"📈 Symbol ready: {symbol} | digits={info.digits} | trade_mode={info.trade_mode}")
    return info

def market_order(symbol, lot, action="BUY", sl_points=None, tp_points=None, deviation=50):
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        raise RuntimeError(f"No tick for {symbol}. Market closed or bad symbol?")

    order_type = mt5.ORDER_TYPE_BUY if action.upper()=="BUY" else mt5.ORDER_TYPE_SELL
    price = tick.ask if order_type==mt5.ORDER_TYPE_BUY else tick.bid

    # Compute SL/TP prices if points given
    sl = None
    tp = None
    if sl_points:
        sl = price - sl_points*mt5.symbol_info(symbol).point if order_type==mt5.ORDER_TYPE_BUY else price + sl_points*mt5.symbol_info(symbol).point
    if tp_points:
        tp = price + tp_points*mt5.symbol_info(symbol).point if order_type==mt5.ORDER_TYPE_BUY else price - tp_points*mt5.symbol_info(symbol).point

    request = {
        "action":   mt5.TRADE_ACTION_DEAL,
        "symbol":   symbol,
        "volume":   float(lot),
        "type":     order_type,
        "price":    price,
        "deviation": deviation,  # slippage
        "magic":    987654,      # your bot's magic
        "comment":  "XAU_Bot test trade",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    if sl: request["sl"] = sl
    if tp: request["tp"] = tp

    logger.info(f"🚀 Sending {action.upper()} {symbol} {lot} @ {price}")
    result = mt5.order_send(request)
    if result is None:
        raise RuntimeError(f"order_send returned None: {mt5.last_error()}")

    logger.info(f"📬 Order result: retcode={result.retcode} | {result._asdict()}")

    # Basic success check
    if result.retcode not in (mt5.TRADE_RETCODE_DONE, mt5.TRADE_RETCODE_PLACED):
        raise RuntimeError(f"Trade rejected: retcode={result.retcode} | {result.comment}")

    return result

def log_trade_jsonl(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")

def main():
    load_dotenv()
    symbol = os.getenv("MT5_SYMBOL", "XAUUSD.sd")
    lot    = float(os.getenv("MT5_LOT", "0.01"))

    initialize_mt5()
    info = ensure_symbol(symbol)

    # Sanity: is trading allowed?
    if info.trade_mode == mt5.SYMBOL_TRADE_MODE_DISABLED:
        raise RuntimeError(f"Trading disabled for {symbol}.")

    # Decide BUY vs SELL for the test (default BUY). Flip to SELL if you prefer.
    action = "BUY"

    result = market_order(symbol, lot, action=action, sl_points=None, tp_points=None, deviation=100)

    payload = {
        "timestamp": datetime.utcnow().isoformat(timespec="seconds"),
        "symbol": symbol,
        "action": action,
        "volume": lot,
        "price": float(result.price) if hasattr(result, "price") and result.price else None,
        "order": result.order,
        "deal": getattr(result, "deal", None),
        "retcode": result.retcode,
        "comment": result.comment,
        "status": "PLACED"
    }
    log_trade_jsonl("reports/live_trade_log.jsonl", payload)
    logger.success(f"✅ Test trade placed. Deal={payload['deal']} Order={payload['order']}")

    # (optional) small wait then print position snapshot
    time.sleep(1.5)
    positions = mt5.positions_get(symbol=symbol)
    logger.info(f"📌 Open positions on {symbol}: {positions}")

    mt5.shutdown()
    logger.info("👋 MT5 shutdown complete.")

if __name__ == "__main__":
    main()
