import pandas as pd
import numpy as np

# ========== Core Indicator Functions ==========

def EMA(series, period):
    return series.ewm(span=period, adjust=False).mean()

def RSI(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def MACD(series, fast=12, slow=26, signal=9):
    ema_fast = EMA(series, fast)
    ema_slow = EMA(series, slow)
    macd = ema_fast - ema_slow
    signal_line = EMA(macd, signal)
    return macd - signal_line

def Bollinger_Bands(series, period=20, num_std=2):
    ma = series.rolling(window=period).mean()
    std = series.rolling(window=period).std()
    upper = ma + num_std * std
    lower = ma - num_std * std
    return upper, lower

def ATR(df, period=14):
    high_low = df['high'] - df['low']
    high_close = np.abs(df['high'] - df['close'].shift())
    low_close = np.abs(df['low'] - df['close'].shift())
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean()
    return atr

# ========== Main Wrapper ==========

def compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # Exponentials
    df["EMA_20"] = EMA(df["close"], 20)
    df["EMA_50"] = EMA(df["close"], 50)
    df["EMA_200"] = EMA(df["close"], 200)

    # RSI
    df["RSI_14"] = RSI(df["close"], 14)

    # MACD
    df["MACD"] = MACD(df["close"])

    # Bollinger Bands
    bb_upper, bb_lower = Bollinger_Bands(df["close"], 20)
    df["BB_upper"] = bb_upper
    df["BB_lower"] = bb_lower

    # ATR
    df["ATR"] = ATR(df, 14)

    # Drop NaNs from warm-up periods
    df.dropna(inplace=True)
    df.reset_index(drop=True, inplace=True)
    return df
