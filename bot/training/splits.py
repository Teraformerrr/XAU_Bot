import numpy as np
from typing import Tuple

def time_series_split(n: int, train_ratio: float, val_ratio: float) -> Tuple[slice, slice, slice]:
    n_train = int(n * train_ratio)
    n_val = int(n * val_ratio)
    n_test = n - n_train - n_val
    if n_test <= 0:
        raise ValueError("Invalid split ratios; test set is empty.")
    train_idx = slice(0, n_train)
    val_idx = slice(n_train, n_train + n_val)
    test_idx = slice(n_train + n_val, n)
    return train_idx, val_idx, test_idx

def drop_tail(X, y, k_tail: int):
    if k_tail <= 0:
        return X, y
    return X[:-k_tail], y[:-k_tail]
