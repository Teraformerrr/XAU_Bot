import numpy as np
import pandas as pd
from typing import List, Tuple, Dict
from sklearn.preprocessing import StandardScaler

class FeatureEngineer:
    def __init__(self, feature_names: List[str], normalize: bool = True):
        self.feature_names = feature_names
        self.normalize = normalize
        self.scaler = None

    def build_matrix(
        self, df: pd.DataFrame, fit: bool = True
    ) -> Tuple[np.ndarray, Dict[str, int]]:
        missing = [f for f in self.feature_names if f not in df.columns]
        if missing:
            raise ValueError(f"Missing features in data: {missing}")

        X = df[self.feature_names].astype(float).values
        if self.normalize:
            if fit or (self.scaler is None):
                self.scaler = StandardScaler()
                X = self.scaler.fit_transform(X)
            else:
                X = self.scaler.transform(X)

        feat_index = {name: i for i, name in enumerate(self.feature_names)}
        return X, feat_index
