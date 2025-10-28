import os
import numpy as np
import pandas as pd
import logging
from tensorflow.keras.models import load_model
from sklearn.preprocessing import MinMaxScaler

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")

# ─────────────────────────────────────────────
# LSTM Prediction Engine
# ─────────────────────────────────────────────
class LSTMPredictor:
    def __init__(
        self,
        model_path="bot/models/lstm/lstm_xauusd_5m.h5",
        lookback=50,
        feature_cols=None
    ):
        self.model_path = model_path
        self.lookback = lookback
        self.feature_cols = feature_cols or [
            "EMA_20","EMA_50","EMA_200","RSI_14","MACD","BB_upper","BB_lower","ATR"
        ]
        self.scaler = MinMaxScaler()
        self.model = None
        self.load_model()

    # ─────────────────────────────────────────
    def load_model(self):
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"❌ LSTM model not found → {self.model_path}")
        self.model = load_model(self.model_path)
        logging.info(f"✅ LSTM model loaded from {self.model_path}")

    # ─────────────────────────────────────────
    def prepare_sequence(self, df: pd.DataFrame):
        """Scale + window latest lookback segment for prediction."""
        df = df.copy().dropna()
        if len(df) < self.lookback:
            raise ValueError(f"❌ Not enough data ({len(df)} rows) for lookback={self.lookback}")

        seq = df[self.feature_cols].values[-self.lookback:]
        scaled = self.scaler.fit_transform(seq)
        X = np.expand_dims(scaled, axis=0)  # (1, lookback, features)
        return X

    # ─────────────────────────────────────────
    def predict(self, df: pd.DataFrame):
        X = self.prepare_sequence(df)
        prob = float(self.model.predict(X, verbose=0)[0][0])
        action = "BUY" if prob > 0.55 else ("SELL" if prob < 0.45 else "HOLD")

        result = {
            "confidence": round(prob, 4),
            "action": action,
            "lookback": self.lookback,
            "features_used": self.feature_cols,
        }
        logging.info(
            f"🤖 LSTM Decision → conf={result['confidence']:.4f} | action={result['action']}"
        )
        return result


# ─────────────────────────────────────────────
# Demo Runner (stand-alone test)
# ─────────────────────────────────────────────
if __name__ == "__main__":
    import pandas as pd

    df = pd.read_csv("bot/data/ohlcv_features.csv").dropna()
    predictor = LSTMPredictor()
    output = predictor.predict(df)
    print(output)
