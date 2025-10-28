import os, sys, atexit

LOCK_FILE = "main.lock"

def ensure_single_instance():
    # If a previous lock exists, read its PID
    if os.path.exists(LOCK_FILE):
        try:
            old_pid = int(open(LOCK_FILE).read().strip())
            # Check if that process is still running
            if old_pid and os.path.exists(f"//./proc/{old_pid}"):
                print(f"⚠️  main.py already running (PID {old_pid}). Exiting...")
                sys.exit(0)
        except Exception:
            pass
        # Remove stale lock if process not found
        try:
            os.remove(LOCK_FILE)
        except:
            pass

    # Create a new lock file
    with open(LOCK_FILE, "w") as f:
        f.write(str(os.getpid()))

    # Auto-delete on exit
    atexit.register(lambda: os.path.exists(LOCK_FILE) and os.remove(LOCK_FILE))

ensure_single_instance()


import os, yaml
import numpy as np
import pandas as pd
from bot.data_feed import MT5Feed
from bot.risk.sharpe_sortino import sharpe_ratio, sortino_ratio, information_ratio, max_drawdown
from bot.risk.cvar_tail import historical_cvar, tail_stats
from bot.utils.logger import banner, kv, info, warn

# Import the scheduler (new)
from bot.core.scheduler import ContinuousScheduler
from bot.core.state_manager import StateManager
from bot.core.error_handler import SafeExecutor   # 🆕


CONFIG = 'D:/XAU_Bot/config.yaml'

# 🔁 Each cycle of bot execution
def run_cycle():
    banner('Phase 1 — Data & Risk Infrastructure')
    state_manager = StateManager()  # 🆕 Persistent state manager

    with open(CONFIG, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    feed = MT5Feed(CONFIG)
    symbol = cfg['mt5']['symbols'][0]
    feat = feed.snapshot_symbol(symbol)

    if feat.empty:
        warn('No data to compute metrics. Ensure MT5 is running and symbol is active.')
        return

    if 'log_ret' not in feat.columns:
        warn("Insufficient data — waiting for more bars to compute indicators.")
        return

    ret = feat['log_ret'].fillna(0)
    sr = sharpe_ratio(ret, rf_annual=cfg['risk_free_rate_annual'], freq='1min')
    so = sortino_ratio(ret, rf_annual=cfg['risk_free_rate_annual'], freq='1min')
    ir = information_ratio(ret, pd.Series(np.zeros(len(ret)), index=ret.index), freq='1min')
    eq = (1 + ret).cumprod()
    mdd = max_drawdown(eq)
    cvar = historical_cvar(ret, alpha=cfg['var_alpha'])
    tails = tail_stats(ret)

    metrics = {
        'Symbol': symbol,
        'Bars': len(feat),
        'Sharpe': round(float(sr), 3) if sr == sr else 'NaN',
        'Sortino': round(float(so), 3) if so == so else 'NaN',
        'Info Ratio': round(float(ir), 3) if ir == ir else 'NaN',
        'Max Drawdown': round(float(mdd), 4) if mdd == mdd else 'NaN',
        f"CVaR ({int(cfg['var_alpha']*100)}%)": round(float(cvar), 6) if cvar == cvar else 'NaN',
        'Skew': round(float(tails['skew']), 3) if tails['skew'] == tails['skew'] else 'NaN',
        'Kurtosis': round(float(tails['kurtosis']), 3) if tails['kurtosis'] == tails['kurtosis'] else 'NaN',
    }

    kv('Metrics', metrics)
    info('Saved tick & indicator CSVs under data/. Phase 1 complete.')

    # 🆕 Save the cycle state after completing metrics
    cycle_no = state_manager.state.get("total_cycles", 0) + 1
    state_manager.record_cycle(cycle_no, metrics)


# 🕒 Continuous scheduler (loop every 10 minutes)
if __name__ == "__main__":
    print("──────────────────────── Phase 3 — Continuous Scheduler ─────────────────────────")
    safe = SafeExecutor(max_retries=3, base_delay=5)

    def safe_run():
        safe.run_safe(run_cycle)

    scheduler = ContinuousScheduler(task_fn=safe_run, interval_sec=600)
    scheduler.start()



# 🔁 Define what happens each cycle
def run_cycle():
    banner('Phase 1 — Data & Risk Infrastructure')

    with open("D:\\XAU_Bot\\config.yaml", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    feed = MT5Feed(CONFIG)
    symbol = cfg['mt5']['symbols'][0]
    feat = feed.snapshot_symbol(symbol)

    if feat.empty:
        warn('No data to compute metrics. Ensure MT5 is running and symbol is active.')
        return

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
