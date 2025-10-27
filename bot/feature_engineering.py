import pandas as pd
import numpy as np


# Convert close prices to log returns per bar


def log_returns(df: pd.DataFrame) -> pd.Series:
return np.log(df['close']).diff()


# Volatility (rolling std of returns)


def realized_volatility(log_ret: pd.Series, window: int = 30) -> pd.Series:
return log_ret.rolling(window).std()


# Mean-reversion helper (z-score of price vs EMA)


def zscore_price_vs_ema(df: pd.DataFrame, ema_col: str = 'ema_mid', window: int = 20) -> pd.Series:
spread = df['close'] - df[ema_col]
mu = spread.rolling(window).mean()
sd = spread.rolling(window).std()
return (spread - mu) / sd