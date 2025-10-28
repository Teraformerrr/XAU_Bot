import os
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
import logging

# ─────────────────────────────────────────────
# Logging
# ─────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")

# ─────────────────────────────────────────────
# Paths
# ─────────────────────────────────────────────
SOURCE_PATH = "bot/data/ohlcv_features.csv"       # Phase-1 file (adjust name if different)
OUTPUT_PATH = "bot/data/lstm_training_data.csv"

# ─────────────────────────────────────────────
# Build LSTM dataset
# ─────────────────────────────────────────────
def build_lstm_dataset(lookahead=5):
    if not os.path.exists(SOURCE_PATH):
        raise FileNotFoundError(f"❌ Source file not found → {SOURCE_PATH}")

    logging.info(f"📂 Loading base features from {SOURCE_PATH}")
    df = pd.read_csv(SOURCE_PATH).dropna()

    # Expected feature columns
    feature_cols = ['EMA_20','EMA_50','EMA_200','RSI_14','MACD','BB_upper','BB_lower','ATR']

    # Verify all exist
    missing = [c for c in feature_cols if c not in df.columns]
    if missing:
        raise ValueError(f"❌ Missing columns in source data: {missing}")

    # Compute binary target → 1 if future price ↑ within N bars
    if 'close' not in df.columns:
        raise ValueError("❌ 'close' column not found in dataset.")
    df['target'] = (df['close'].shift(-lookahead) > df['close']).astype(int)

    # Standardize features
    scaler = StandardScaler()
    scaled = scaler.fit_transform(df[feature_cols])
    scaled_df = pd.DataFrame(scaled, columns=feature_cols)
    scaled_df['target'] = df['target']

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    scaled_df.to_csv(OUTPUT_PATH, index=False)

    logging.info(f"✅ LSTM training data saved → {OUTPUT_PATH}")
    logging.info(f"📊 Final shape: {scaled_df.shape}")

# ─────────────────────────────────────────────
# Run
# ─────────────────────────────────────────────
if __name__ == "__main__":
    build_lstm_dataset()
