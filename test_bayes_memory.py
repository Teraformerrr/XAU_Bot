from bot.engines.bayes_memory import BayesianMemory
import numpy as np

mem = BayesianMemory("bayes_state.json")

# Simulate recent volatility pattern
vols = np.random.normal(0.001, 0.0002, 50)
vols[-10:] *= 1.3  # simulate sudden jump

if mem.detect_drift("XAUUSD", vols.tolist()):
    mem.apply_drift_correction("XAUUSD")
