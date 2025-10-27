# D:\XAU_Bot\bot\tests\test_bayes_confidence.py
from __future__ import annotations
from pathlib import Path
from bot.models.bayes_confidence import BayesianConfidenceEngine, SignalEvidence

def run_demo():
    state_path = Path(__file__).parents[1] / "state" / "bayes_state_demo.json"
    eng = BayesianConfidenceEngine(state_path=state_path)

    symbol = "XAUUSD"
    direction = "buy"

    # Strong agreement across 3 signals
    evidence = {
        "kf_trend":   SignalEvidence(True, 0.9),
        "ou_revert":  SignalEvidence(True, 0.6),
        "stoch_momo": SignalEvidence(True, 0.7),
    }
    p = eng.compute_confidence(symbol, direction, evidence)
    print("High-agreement P=", p)

    # Mixed/conflicting signals
    evidence2 = {
        "kf_trend":   SignalEvidence(True, 0.4),
        "ou_revert":  SignalEvidence(False, 0.8),
        "stoch_momo": SignalEvidence(None, 0.0),
    }
    p2 = eng.compute_confidence(symbol, "sell", evidence2)
    print("Mixed P=", p2)

if __name__ == "__main__":
    run_demo()
