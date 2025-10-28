# ================================================================
# File: D:\XAU_Bot\bot\data_feed.py
# Purpose: MT5 data feed, OHLCV conversion, and indicator features
# Updated: Phase 2 — Stable Infrastructure (UTF-8 + Safe Config Loader)
# ================================================================

from __future__ import annotations
import MetaTrader5 as mt5
import pandas as pd
import numpy as np
import yaml
from pathlib import Path
from datetime import datetime, timedelta
from ta.trend import EMAIndicator, MACD
from ta.volatility import BollingerBands, AverageTrueRange
from ta.momentum import RSIIndicator


# ================================================================
# MT5 Feed Class
# ================================================================
class MT5Feed:
    def __init__(self, config: dict | str | None = None):
        """
        Initializes MT5 feed and loads configuration safely.
        Accepts:
          - dict: already loaded config
          - str:  path to config file
          - None: defaults to D:\XAU_Bot\config.yaml
        """
        if isinstance(config, dict):
            # already parsed config
            self.cfg = config
        elif isinstance(config, str):
            # file path passed as string
            with open(config, encoding="utf-8") as f:
                self.cfg = yaml.safe_load(f)
        else:
            # fallback to default config file
            cfg_path = Path("D:\\XAU_Bot\\config.yaml")
            with open(cfg_path, encoding="utf-8") as f:
                self.cfg = yaml.safe_load(f)

        # --- Core Config ---
        self.symbols = self.cfg["mt5"]["symbols"]
        self.timeframe = self.cfg["mt5"].get("timeframe", "M5")
        self.lookback = self.cfg["mt5"].get("lookback_bars", 5000)
        self.refresh = self.cfg["mt5"].get("refresh_rate", 60)
        self.resample_rule = self.cfg.get("resample_rule", "1min").replace("T", "min")

        # --- Connect to MT5 ---
        if not mt5.initialize():
            raise RuntimeError("❌ MT5 initialization failed.")
        print("INFO: Connected to MT5")

    # ============================================================
    # Tick → OHLCV Conversion
    # ============================================================
    def fetch_ticks(self, symbol: str, minutes: int = 1) -> pd.DataFrame:
        """
        Fetches recent ticks for the symbol using broker/server time.
        Falls back to UTC if MT5 server time unavailable.
        """
        info = mt5.symbol_info_tick(symbol)
        if info is None:
            raise ValueError(f"Symbol {symbol} not found or inactive in MT5.")

        # use MT5 server time if available
        now = datetime.fromtimestamp(info.time, tz=None)
        frm = now - timedelta(minutes=minutes)

        ticks = mt5.copy_ticks_range(symbol, frm, now, mt5.COPY_TICKS_ALL)
        if ticks is None or len(ticks) == 0:
            raise ValueError(f"No tick data returned for {symbol} between {frm} and {now}")

        df = pd.DataFrame(ticks)
        df["time"] = pd.to_datetime(df["time"], unit="s")
        df.set_index("time", inplace=True)
        return df

    def ticks_to_bars(self, tick_df: pd.DataFrame) -> pd.DataFrame:
        """
        Convert tick-level data into OHLCV bars safely.
        Handles bid/ask/last-only data and normalizes timestamps.
        """
        import pandas as pd

        if tick_df.empty:
            print("⚠️ Tick dataframe is empty — cannot convert to bars.")
            return pd.DataFrame()

        # --- Detect price column dynamically ---
        price_col = None
        for col in ["bid", "ask", "last"]:
            if col in tick_df.columns:
                price_col = col
                break
        if price_col is None:
            raise ValueError("No bid/ask/last column found in tick data.")

        # --- Ensure time index is proper datetime in UTC ---
        if not pd.api.types.is_datetime64_any_dtype(tick_df.index):
            if "time" in tick_df.columns:
                tick_df["time"] = pd.to_datetime(tick_df["time"], unit="s", utc=True)
                tick_df.set_index("time", inplace=True)
            else:
                raise ValueError("No time column found in tick data.")
        else:
            tick_df.index = pd.to_datetime(tick_df.index, utc=True)

        # --- Sort and remove duplicates ---
        tick_df = tick_df[~tick_df.index.duplicated(keep="last")].sort_index()

        # --- Normalize to 1-second precision ---
        tick_df.index = tick_df.index.floor("S")

        # --- Resample safely to 1-minute OHLC bars ---
        rule = self.resample_rule if hasattr(self, "resample_rule") else "1min"
        price_series = tick_df[price_col]
        o = price_series.resample(rule).first()
        h = price_series.resample(rule).max()
        l = price_series.resample(rule).min()
        c = price_series.resample(rule).last()

        # --- Volume aggregation ---
        if "volume" in tick_df.columns:
            v = tick_df["volume"].resample(rule).sum()
        else:
            v = pd.Series(0, index=c.index)

        bars = pd.concat([o, h, l, c, v], axis=1)
        bars.columns = ["open", "high", "low", "close", "volume"]
        bars.dropna(inplace=True)

        print(f"✅ Converted {len(tick_df)} ticks → {len(bars)} bars ({rule})")
        return bars

    # ============================================================
    # Indicator Calculations
    # ============================================================
    def add_indicators(self, df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
        """
        Add technical indicators safely without dropping short datasets.
        """
        import ta  # technical analysis library
        import numpy as np

        if df.empty:
            print("⚠️ Empty DataFrame received in add_indicators()")
            return df

        df = df.copy()

        # --- Core EMAs ---
        for p in [20, 50, 200]:
            try:
                df[f"EMA_{p}"] = df["close"].ewm(span=p, adjust=False).mean()
            except Exception as e:
                print(f"⚠️ EMA({p}) failed: {e}")
                df[f"EMA_{p}"] = np.nan

        # --- RSI ---
        try:
            df["RSI_14"] = ta.momentum.RSIIndicator(df["close"], window=14).rsi()
        except Exception as e:
            print("⚠️ RSI failed:", e)
            df["RSI_14"] = np.nan

        # --- MACD ---
        try:
            macd = ta.trend.MACD(df["close"])
            df["MACD"] = macd.macd()
            df["MACD_Signal"] = macd.macd_signal()
            df["MACD_Hist"] = macd.macd_diff()
        except Exception as e:
            print("⚠️ MACD failed:", e)
            df["MACD"] = df["MACD_Signal"] = df["MACD_Hist"] = np.nan

        # --- Bollinger Bands ---
        try:
            bb = ta.volatility.BollingerBands(df["close"], window=20, window_dev=2)
            df["BB_Mid"] = bb.bollinger_mavg()
            df["BB_Upper"] = bb.bollinger_hband()
            df["BB_Lower"] = bb.bollinger_lband()
        except Exception as e:
            print("⚠️ Bollinger Bands failed:", e)
            df["BB_Mid"] = df["BB_Upper"] = df["BB_Lower"] = np.nan

        # --- ATR ---
        try:
            df["ATR"] = ta.volatility.AverageTrueRange(
                high=df["high"], low=df["low"], close=df["close"], window=14
            ).average_true_range()
        except Exception as e:
            print("⚠️ ATR failed:", e)
            df["ATR"] = np.nan

        # --- Fill any remaining NaNs rather than dropping ---
        df.fillna(method="bfill", inplace=True)
        df.fillna(method="ffill", inplace=True)

        print(f"✅ Indicators added → {len(df)} rows, {df.isna().sum().sum()} NaNs remaining")
        return df

    # ============================================================
    # Snapshot Symbol Features
    # ============================================================
    def snapshot_symbol(self, symbol: str) -> pd.DataFrame:
        """
        Fetch enough market data → OHLC bars → indicators for a given symbol.
        Uses ticks if available, else falls back to historical OHLC data (guaranteed).
        """
        from datetime import datetime, timedelta
        atr_period = self.cfg.get("indicators", {}).get("atr_period", 14)
        fetch_minutes = 720  # 12 hours of 1-minute data


        df_ticks = pd.DataFrame()

        # --- Try live ticks (using MT5 server time) ---
        try:
            info = mt5.symbol_info_tick(symbol)
            if info:
                now = datetime.fromtimestamp(info.time)
                frm = now - timedelta(minutes=fetch_minutes)
                ticks = mt5.copy_ticks_range(symbol, frm, now, mt5.COPY_TICKS_ALL)
                if ticks is not None and len(ticks) > 0:
                    df_ticks = pd.DataFrame(ticks)
                    df_ticks["time"] = pd.to_datetime(df_ticks["time"], unit="s")
                    df_ticks.set_index("time", inplace=True)
                    print(f"✅ {symbol}: Live ticks fetched → {len(df_ticks)}")
        except Exception as e:
            print(f"⚠️ Tick fetch error: {e}")

        # --- Fallback: historical OHLC bars ---
        if df_ticks.empty:
            try:
                utc_from = datetime.now() - timedelta(days=5)
                rates = mt5.copy_rates_from(symbol, mt5.TIMEFRAME_M1, utc_from, 5000)
                if rates is not None and len(rates) > 0:
                    df_ticks = pd.DataFrame(rates)
                    df_ticks["time"] = pd.to_datetime(df_ticks["time"], unit="s")
                    df_ticks.set_index("time", inplace=True)
                    print(f"✅ {symbol}: Historical OHLC fetched → {len(df_ticks)} bars")
                else:
                    print(f"⚠️ No tick or OHLC data available for {symbol}.")
            except Exception as e:
                print(f"❌ Failed to fetch historical data: {e}")
                return pd.DataFrame()

        # --- Normalize columns for indicator generation ---
        if "bid" in df_ticks.columns:
            df_ticks.rename(columns={"bid": "close"}, inplace=True)
        if "ask" in df_ticks.columns and "close" not in df_ticks.columns:
            df_ticks.rename(columns={"ask": "close"}, inplace=True)
        if "open" not in df_ticks.columns:
            df_ticks["open"] = df_ticks["close"]
        if "high" not in df_ticks.columns:
            df_ticks["high"] = df_ticks["close"]
        if "low" not in df_ticks.columns:
            df_ticks["low"] = df_ticks["close"]
        if "volume" not in df_ticks.columns:
            df_ticks["volume"] = 0

        bars = self.ticks_to_bars(df_ticks)
        if len(bars) < atr_period:
            print(f"⚠️ Only {len(bars)} bars — not enough for ATR({atr_period}).")

        feat = self.add_indicators(bars, self.cfg)
        return feat



# ================================================================
# Standalone Test
# ================================================================
if __name__ == "__main__":
    cfg_path = Path("D:\\XAU_Bot\\config.yaml")
    with open(cfg_path, encoding="utf-8") as f:
        CONFIG = yaml.safe_load(f)

    feed = MT5Feed(CONFIG)
    symbol = CONFIG["mt5"]["symbols"][0]
    features = feed.snapshot_symbol(symbol)
    print(f"\n✅ {symbol} Indicator Snapshot:")
    print(features.tail(10))
