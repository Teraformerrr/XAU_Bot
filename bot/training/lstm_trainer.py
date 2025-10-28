import os
import json
import numpy as np
import pandas as pd
from datetime import datetime
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout
from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint
from sklearn.preprocessing import MinMaxScaler
import logging

# ─────────────────────────────────────────────
# Logging Setup
# ─────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")

# ─────────────────────────────────────────────
# LSTM Trainer Class
# ─────────────────────────────────────────────
class LSTMTrainer:
    def __init__(self, data_path="bot/data/lstm_training_data.csv", model_path="bot/models/lstm/lstm_xauusd_5m.h5"):
        self.data_path = data_path
        self.model_path = model_path
        self.scaler = MinMaxScaler()
        self.lookback = 50  # number of past timesteps to look at
        self.model = None

    def load_data(self):
        logging.info(f"📂 Loading dataset: {self.data_path}")
        df = pd.read_csv(self.data_path)
        df = df.dropna()

        # Expect target column named 'target' (1=BUY, 0=SELL)
        features = df.drop(columns=['target']).values
        labels = df['target'].values

        scaled = self.scaler.fit_transform(features)
        X, y = [], []

        for i in range(self.lookback, len(scaled)):
            X.append(scaled[i - self.lookback:i])
            y.append(labels[i])

        X, y = np.array(X), np.array(y)
        logging.info(f"✅ Data shaped: X={X.shape}, y={y.shape}")
        return X, y

    def build_model(self, input_shape):
        logging.info(f"🧱 Building LSTM model with input shape: {input_shape}")
        model = Sequential([
            LSTM(128, return_sequences=True, input_shape=input_shape),
            Dropout(0.3),
            LSTM(64),
            Dropout(0.3),
            Dense(32, activation='relu'),
            Dense(1, activation='sigmoid')
        ])
        model.compile(optimizer='adam', loss='binary_crossentropy', metrics=['accuracy'])
        self.model = model
        logging.info("✅ Model compiled successfully")

    def train(self, X, y, epochs=40, batch_size=64):
        if self.model is None:
            self.build_model((X.shape[1], X.shape[2]))

        checkpoint_cb = ModelCheckpoint(self.model_path, save_best_only=True, monitor='val_accuracy', mode='max')
        early_stop_cb = EarlyStopping(monitor='val_loss', patience=5, restore_best_weights=True)

        history = self.model.fit(
            X, y,
            validation_split=0.2,
            epochs=epochs,
            batch_size=batch_size,
            callbacks=[checkpoint_cb, early_stop_cb],
            verbose=1
        )

        logging.info(f"📦 Model saved → {self.model_path}")
        self.save_training_report(history)
        return history

    def save_training_report(self, history):
        metrics_path = "models/lstm/metrics_lstm.json"
        os.makedirs(os.path.dirname(metrics_path), exist_ok=True)

        report = {
            "timestamp": datetime.utcnow().isoformat(),
            "final_accuracy": float(history.history['accuracy'][-1]),
            "val_accuracy": float(history.history['val_accuracy'][-1]),
            "loss": float(history.history['loss'][-1]),
            "val_loss": float(history.history['val_loss'][-1]),
            "epochs": len(history.history['loss'])
        }

        with open(metrics_path, "w") as f:
            json.dump(report, f, indent=4)

        logging.info(f"📝 Training metrics saved → {metrics_path}")

# ─────────────────────────────────────────────
# Main Runner
# ─────────────────────────────────────────────
if __name__ == "__main__":
    trainer = LSTMTrainer()
    X, y = trainer.load_data()
    trainer.train(X, y)
    logging.info("🏁 LSTM Training complete.")
