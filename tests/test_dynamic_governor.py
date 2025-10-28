# D:\XAU_Bot\tests\test_dynamic_governor.py
from pathlib import Path
import json
import time

from bot.risk.dynamic_governor import DynamicRiskGovernor, DRGConfig, STATE_DIR, RISK_STATE, COMMANDS_FILE

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / "state"
STATE.mkdir(parents=True, exist_ok=True)
PORTFOLIO_STATE = STATE / "portfolio_state.json"

def write_portfolio(**kwargs):
    payload = {
        "equity": kwargs.get("equity", 100000.0),
        "max_drawdown_pct": kwargs.get("dd", 0.0),
        "open_exposure_pct": kwargs.get("exposure", 0.0),
        "margin_level": kwargs.get("margin", 500.0),
        "model_confidence_avg": kwargs.get("avg_conf", 0.60),
        "open_positions": kwargs.get("positions", []),
    }
    PORTFOLIO_STATE.write_text(json.dumps(payload, indent=2), encoding="utf-8")

def read_json(p: Path):
    if not p.exists(): return {}
    return json.loads(p.read_text(encoding="utf-8"))

def count_cmd(cmds, kind):
    return sum(1 for c in cmds.get("commands", []) if c.get("type") == kind)

def test_sanity_and_antispam():
    cfg = DRGConfig(eval_interval_sec=1, hedge_cooldown_sec=60)

    # Normal regime
    write_portfolio(dd=0.03, exposure=0.05, margin=400.0, avg_conf=0.68, positions=[])
    drg = DynamicRiskGovernor(cfg)
    out1 = drg.evaluate_once()
    assert out1["paused"] is False

    # Soft DD → scale down
    write_portfolio(dd=0.12, exposure=0.05, margin=400.0, avg_conf=0.60)
    out2 = drg.evaluate_once()
    assert out2["lot_scale"] < 1.0

    # Hedge condition
    write_portfolio(dd=0.05, exposure=0.10, margin=300.0,
                    positions=[{"symbol": "XAUUSD", "lots": 2.0, "loss_pct": 0.25}])
    out3 = drg.evaluate_once()
    cmds3 = out3["commands"]
    assert count_cmd(cmds3, "REQUEST_HEDGE") == 1

    # Immediately evaluate again with same loss/lots → should NOT re-issue (cooldown throttles)
    out4 = drg.evaluate_once()
    cmds4 = out4["commands"]
    assert count_cmd(cmds4, "REQUEST_HEDGE") == 0

    # Increase loss_pct by > 1pp → should re-issue (passes delta filter)
    write_portfolio(dd=0.05, exposure=0.10, margin=300.0,
                    positions=[{"symbol": "XAUUSD", "lots": 2.0, "loss_pct": 0.27}])
    out5 = drg.evaluate_once()
    cmds5 = out5["commands"]
    assert count_cmd(cmds5, "REQUEST_HEDGE") == 1

    # Artifacts exist
    assert RISK_STATE.exists()
    assert COMMANDS_FILE.exists()

    print("✅ DRG anti-spam tests passed.")

if __name__ == "__main__":
    test_sanity_and_antispam()
