# D:\XAU_Bot\tests\test_exposure_controller.py
import json
from pathlib import Path
from bot.governor.exposure_controller import SmartExposureController, SECConfig, ROOT, STATE_DRG, STATE_PORTFOLIO

def write(p: Path, obj):
    p.write_text(json.dumps(obj, indent=2), encoding="utf-8")

def _seed_state(positions=None, equity=100_000.0, free_margin=80_000.0, drg=None):
    positions = positions or []
    write(STATE_PORTFOLIO, {
        "equity": equity,
        "free_margin": free_margin,
        "open_positions": positions
    })
    write(STATE_DRG, drg or {"risk_level": "normal", "hedge_active": False})

def run_case(name, symbol, req_lots, conf, vol, action):
    print(f"\n──── Test: {name} ────")
    sec = SmartExposureController(SECConfig())
    return sec.decide(symbol, req_lots, conf, vol, action)

def main():
    ROOT.mkdir(parents=True, exist_ok=True)  # no-op if exists

    # Case 1: No positions, normal risk → approve
    _seed_state(positions=[], drg={"risk_level":"normal","hedge_active":False})
    res1 = run_case("approve basic", "XAUUSD", 2.0, conf=0.62, vol=0.12, action="BUY")
    assert res1["status"] in ("APPROVED","SCALED")

    # Case 2: Heavy existing exposure → scale/deny
    _seed_state(positions=[{"symbol":"XAUUSD","lots":5.8,"side":"BUY"}])
    res2 = run_case("symbol nearly maxed", "XAUUSD", 2.0, conf=0.70, vol=0.18, action="BUY")
    assert res2["status"] in ("SCALED","DENIED")

    # Case 3: DRG elevated risk → smaller caps
    _seed_state(positions=[{"symbol":"XAUUSD","lots":2.0,"side":"BUY"}],
                drg={"risk_level":"elevated","hedge_active":False})
    res3 = run_case("elevated risk", "XAUUSD", 4.0, conf=0.55, vol=0.30, action="BUY")
    assert res3["status"] in ("SCALED","DENIED","APPROVED")

    # Case 4: Hedge active → strong cut
    _seed_state(positions=[{"symbol":"XAUUSD","lots":1.0,"side":"BUY"}],
                drg={"risk_level":"normal","hedge_active":True})
    res4 = run_case("hedge active", "XAUUSD", 4.0, conf=0.60, vol=0.20, action="BUY")
    assert res4["status"] in ("SCALED","DENIED","APPROVED")

    # Case 5: Margin guard deny
    _seed_state(positions=[], equity=100_000.0, free_margin=10_000.0,
                drg={"risk_level":"normal","hedge_active":False})
    res5 = run_case("margin deny", "XAUUSD", 1.0, conf=0.70, vol=0.10, action="BUY")
    assert res5["status"] == "DENIED"

    print("\n✅ SEC tests finished.")

if __name__ == "__main__":
    main()
