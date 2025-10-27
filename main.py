import os, yaml
import numpy as np
import pandas as pd
from bot.data_feed import MT5Feed
from bot.risk.sharpe_sortino import sharpe_ratio, sortino_ratio, information_ratio, max_drawdown
from bot.risk.cvar_tail import historical_cvar, tail_stats
from bot.utils.logger import banner, kv, info, warn

CONFIG = 'D:/XAU_Bot/config.yaml'

if __name__ == '__main__':
    banner('Phase 1 — Data & Risk Infrastructure')

    with open("D:\\XAU_Bot\\config.yaml", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    feed = MT5Feed(CONFIG)
    symbol = cfg['mt5']['symbols'][0]
    feat = feed.snapshot_symbol(symbol)

    if feat.empty:
        warn('No data to compute metrics. Ensure MT5 is running and symbol is active.')
        raise SystemExit(0)

    # ✅ Ensure log_ret column exists
    if 'log_ret' not in feat.columns:
        warn("Insufficient data — waiting for more bars to compute indicators.")
        warn("Keep MT5 open for a few minutes and rerun to collect ~30–50 bars.")
        raise SystemExit(0)

    # Compute risk metrics
    ret = feat['log_ret'].fillna(0)

    sr = sharpe_ratio(ret, rf_annual=cfg['risk_free_rate_annual'], freq='1min')
    so = sortino_ratio(ret, rf_annual=cfg['risk_free_rate_annual'], freq='1min')
    ir = information_ratio(ret, pd.Series(np.zeros(len(ret)), index=ret.index), freq='1min')

    eq = (1 + ret).cumprod()
    mdd = max_drawdown(eq)

    cvar = historical_cvar(ret, alpha=cfg['var_alpha'])
    tails = tail_stats(ret)

    kv('Metrics', {
        'Symbol': symbol,
        'Bars': len(feat),
        'Sharpe': round(float(sr), 3) if sr == sr else 'NaN',
        'Sortino': round(float(so), 3) if so == so else 'NaN',
        'Info Ratio': round(float(ir), 3) if ir == ir else 'NaN',
        'Max Drawdown': round(float(mdd), 4) if mdd == mdd else 'NaN',
        f"CVaR ({int(cfg['var_alpha']*100)}%)": round(float(cvar), 6) if cvar == cvar else 'NaN',
        'Skew': round(float(tails['skew']), 3) if tails['skew'] == tails['skew'] else 'NaN',
        'Kurtosis': round(float(tails['kurtosis']), 3) if tails['kurtosis'] == tails['kurtosis'] else 'NaN',
    })

    info('Saved tick & indicator CSVs under data/. Phase 1 complete.')
