from bot.tuning.volatility_tuner import VolatilityAwareTuner
import random

if __name__ == "__main__":
    tuner = VolatilityAwareTuner()
    for i in range(60):
        conf = random.uniform(0.4, 0.6)
        vol = random.uniform(0.02, 0.25)
        tuner.update(conf, vol)
        if i % 10 == 0:
            buy_th, sell_th, nb = tuner.tuned_thresholds()
            print(f"Cycle {i}: BUY={buy_th:.3f}, SELL={sell_th:.3f}, NB={nb:.3f}")
