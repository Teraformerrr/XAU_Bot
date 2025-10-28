import os
import pandas as pd
import numpy as np
import logging
from ta.trend import EMAIndicator, MACD
from ta.volatility import BollingerBands
from ta.momentum import RSIIndicator
from ta.volatility import AverageTrueRange

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")

OUTPUT_PATH = "bot/data/ohlcv_features.csv"

def generate_features():
    logging.info("📊 Generating synthetic OHLCV + indicator dataset for XAUUSD")

    # Create fake but structured OHLCV data for 5-min intervals (for testing)
    n = 5000  # number of samples
    np.random.seed(42)
    time_index = pd.date_range(start="2024-01-01", periods=n, freq="5T")

    prices = np.cumsum(np.random.randn(n)) + 2380  # around gold price range
    high = prices + np.random.rand(n) * 2
    low = prices - np.random.rand(n) * 2
    close = prices + np.random.randn(n) * 0.5
    volume = np.random.randint(100, 1000, size=n)

    df = pd.DataFrame({
        'time': time_index,
        'open': prices,
        'high': high,
        'low': low,
        'close': close,
        'volume': volume
    })

    # Indicators
    df['EMA_20'] = EMAIndicator(df['close'], window=20).ema_indicator()
    df['EMA_50'] = EMAIndicator(df['close'], window=50).ema_indicator()
    df['EMA_200'] = EMAIndicator(df['close'], window=200).ema_indicator()
    df['RSI_14'] = RSIIndicator(df['close'], window=14).rsi()
    macd = MACD(df['close'])
    df['MACD'] = macd.macd()
    bb = BollingerBands(df['close'])
    df['BB_upper'] = bb.bollinger_hband()
    df['BB_lower'] = bb.bollinger_lband()
    df['ATR'] = AverageTrueRange(df['high'], df['low'], df['close'], window=14).average_true_range()

    df = df.dropna()
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    df.to_csv(OUTPUT_PATH, index=False)
    logging.info(f"✅ Feature dataset saved → {OUTPUT_PATH}")
    logging.info(f"📏 Final shape: {df.shape}")

if __name__ == "__main__":
    generate_features()
