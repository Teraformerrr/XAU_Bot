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
        Fetches recent ticks for the symbol.
        """
        now = datetime.utcnow()
        frm = now - timedelta(minutes=minutes)
        ticks = mt5.copy_ticks_range(symbol, frm, now, mt5.COPY_TICKS_ALL)
        if ticks is None or len(ticks) == 0:
            raise ValueError(f"No tick data returned for {symbol}")
        df = pd.DataFrame(ticks)
        df["time"] = pd.to_datetime(df["time"], unit="s", utc=True)
        df = df.set_index("time")
        return df

    def ticks_to_bars(self, tick_df: pd.DataFrame) -> pd.DataFrame:
        """
        Resamples tick data into OHLCV bars.
        """
        price_series = tick_df["bid"]
        rule = self.resample_rule
        o = price_series.resample(rule).first()
        h = price_series.resample(rule).max()
        l = price_series.resample(rule).min()
        c = price_series.resample(rule).last()
        v = tick_df.get("volume", pd.Series(0, index=c.index)).resample(rule).sum()
        df = pd.concat([o, h, l, c, v], axis=1)
        df.columns = ["open", "high", "low", "close", "volume"]
        df.dropna(inplace=True)
        return df

    # ============================================================
    # Indicator Calculations
    # ============================================================
    def add_indicators(self, df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
        """
        Adds EMA, RSI, MACD, Bollinger Bands, ATR indicators.
        """
        if df.empty:
            raise ValueError("DataFrame is empty, cannot add indicators.")

        # --- Safe indicator configuration lookup ---
        ind_cfg = cfg.get("indicators", {})

        ema_periods = ind_cfg.get("ema_periods", [20, 50, 200])
        ema_fast = ind_cfg.get("ema_fast", ema_periods[0])
        ema_slow = ind_cfg.get("ema_slow", ema_periods[1])
        ema_long = ind_cfg.get("ema_long", ema_periods[2])

        rsi_period = ind_cfg.get("rsi_period", cfg.get("rsi_period", 14))
        macd_fast = ind_cfg.get("macd_fast", cfg.get("macd_fast", 12))
        macd_slow = ind_cfg.get("macd_slow", cfg.get("macd_slow", 26))
        macd_signal = ind_cfg.get("macd_signal", cfg.get("macd_signal", 9))
        bb_period = ind_cfg.get("bb_period", cfg.get("bb_period", 20))
        bb_stddev = ind_cfg.get("bb_stddev", cfg.get("bb_stddev", 2))
        atr_period = ind_cfg.get("atr_period", cfg.get("atr_period", 14))

        # --- Compute indicators ---
        df["EMA_Fast"] = EMAIndicator(df["close"], window=ema_fast).ema_indicator()
        df["EMA_Slow"] = EMAIndicator(df["close"], window=ema_slow).ema_indicator()
        df["EMA_Long"] = EMAIndicator(df["close"], window=ema_long).ema_indicator()

        df["RSI"] = RSIIndicator(df["close"], window=rsi_period).rsi()

        macd_calc = MACD(
            df["close"],
            window_slow=macd_slow,
            window_fast=macd_fast,
            window_sign=macd_signal,
        )
        df["MACD"] = macd_calc.macd()
        df["MACD_Signal"] = macd_calc.macd_signal()
        df["MACD_Hist"] = macd_calc.macd_diff()

        bb = BollingerBands(df["close"], window=bb_period, window_dev=bb_stddev)
        df["BB_Mid"] = bb.bollinger_mavg()
        df["BB_Upper"] = bb.bollinger_hband()
        df["BB_Lower"] = bb.bollinger_lband()

        atr_calc = AverageTrueRange(df["high"], df["low"], df["close"], window=atr_period)
        df["ATR"] = atr_calc.average_true_range()

        return df.dropna()

    # ============================================================
    # Snapshot Symbol Features
    # ============================================================
    def snapshot_symbol(self, symbol: str) -> pd.DataFrame:
        """
        Fetches enough tick data → bars → indicators for a given symbol.
        Auto-expands minutes so indicators like ATR(14) and EMA(200) have data.
        """
        atr_period = self.cfg.get("indicators", {}).get("atr_period", 14)
        fetch_minutes = max(atr_period * 2, 30)  # 30 min or 2×ATR window

        tick_df = self.fetch_ticks(symbol, minutes=fetch_minutes)
        bars = self.ticks_to_bars(tick_df)

        # prevent ATR crash if dataset too short
        if len(bars) < atr_period:
            print(f"⚠️  Only {len(bars)} bars — not enough for ATR({atr_period}).")
        feat = self.add_indicators(bars, self.cfg)
        return feat.tail(5)


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
