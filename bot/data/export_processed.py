import pandas as pd
from pathlib import Path
import MetaTrader5 as mt5
from bot.data.indicator_engine import compute_indicators
  # adjust if your indicators module name differs

def export_processed(symbol="XAUUSD.sd", timeframe=mt5.TIMEFRAME_M5, bars=5000):
    print(f"📊 Exporting {symbol} M5 data with indicators...")

    # 1️⃣ Connect to MT5
    if not mt5.initialize():
        raise RuntimeError("❌ Failed to connect to MT5 terminal.")
    info = mt5.account_info()
    print(f"✅ Connected to {info.name} | Equity: {info.equity}")

    # 2️⃣ Fetch OHLCV data
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, bars)
    if rates is None or len(rates) == 0:
        raise ValueError(f"No data received for {symbol}. Check Market Watch visibility.")

    # 3️⃣ Convert to DataFrame
    df = pd.DataFrame(rates)
    df["time"] = pd.to_datetime(df["time"], unit="s")
    df.rename(columns={
        "open": "open",
        "high": "high",
        "low": "low",
        "close": "close",
        "tick_volume": "volume"
    }, inplace=True)
    df = df[["time", "open", "high", "low", "close", "volume"]]

    # 4️⃣ Compute indicators
    df = compute_indicators(df)

    # 5️⃣ Save to data/processed
    out_dir = Path("data/processed")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "xauusd_5m.csv"
    df.to_csv(out_path, index=False)

    print(f"✅ Saved processed dataset → {out_path}")
    print(f"📈 Total rows: {len(df)}")

    mt5.shutdown()
    print("🔌 MT5 connection closed.")

if __name__ == "__main__":
    export_processed()
