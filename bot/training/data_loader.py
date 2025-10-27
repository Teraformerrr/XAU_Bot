import pandas as pd
from pathlib import Path

REQUIRED_COLS = ["time","open","high","low","close","volume"]

class DataLoader:
    def __init__(self, csv_path: str):
        self.csv_path = Path(csv_path)

    def load(self) -> pd.DataFrame:
        if not self.csv_path.exists():
            raise FileNotFoundError(f"Data file not found: {self.csv_path}")
        df = pd.read_csv(self.csv_path)
        # Ensure required cols
        for c in REQUIRED_COLS:
            if c not in df.columns:
                raise ValueError(f"Missing required column: {c}")
        # Ensure time is datetime and sorted
        df["time"] = pd.to_datetime(df["time"])
        df = df.sort_values("time").reset_index(drop=True)
        return df
