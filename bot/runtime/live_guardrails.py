import os
import yaml
import json
import datetime as dt
from pathlib import Path

GUARD_FILE = Path("bot/state/trade_guard.json")

class TradeGuard:
    def __init__(self, config_path="config.yaml"):
        with open(config_path, "r", encoding="utf-8") as f:
            self.cfg = yaml.safe_load(f)

        self.cooldown_bars = int(self.cfg["engine"].get("cool_down_bars", 5))
        self.max_open = int(self.cfg["engine"].get("max_open_positions", 3))
        self.daily_target = float(self.cfg.get("daily_profit_target_usd", 1000))
        self.daily_loss = float(self.cfg.get("daily_loss_limit_usd", -500))
        self._load_state()

    def _load_state(self):
        if GUARD_FILE.exists():
            self.state = json.load(open(GUARD_FILE))
        else:
            self.state = {"last_trade_bar": 0, "open_positions": 0,
                          "daily_pnl": 0.0, "date": dt.date.today().isoformat()}
            self._save_state()

    def _save_state(self):
        GUARD_FILE.parent.mkdir(parents=True, exist_ok=True)
        json.dump(self.state, open(GUARD_FILE, "w"), indent=2)

    # Reset at new trading day
    def reset_if_new_day(self):
        if self.state["date"] != dt.date.today().isoformat():
            self.state.update({
                "last_trade_bar": 0,
                "open_positions": 0,
                "daily_pnl": 0.0,
                "date": dt.date.today().isoformat()
            })
            self._save_state()

    def record_trade(self, pnl=0.0, bar_index=0):
        self.state["last_trade_bar"] = bar_index
        self.state["open_positions"] += 1
        self.state["daily_pnl"] += pnl
        self._save_state()

    def close_trade(self, pnl=0.0):
        self.state["open_positions"] = max(0, self.state["open_positions"] - 1)
        self.state["daily_pnl"] += pnl
        self._save_state()

    def can_trade(self, current_bar_index: int):
        self.reset_if_new_day()
        reasons = []

        # 1. Daily stop
        if self.state["daily_pnl"] >= self.daily_target:
            reasons.append("Daily target reached")
        if self.state["daily_pnl"] <= self.daily_loss:
            reasons.append("Daily loss limit hit")

        # 2. Max open
        if self.state["open_positions"] >= self.max_open:
            reasons.append("Max open positions reached")

        # 3. Cooldown
        if current_bar_index - self.state["last_trade_bar"] < self.cooldown_bars:
            reasons.append("Cooldown not complete")

        allowed = len(reasons) == 0
        return allowed, reasons
