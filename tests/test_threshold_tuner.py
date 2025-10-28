from bot.engines.threshold_tuner import ThresholdTuner

if __name__ == "__main__":
    tuner = ThresholdTuner()
    result = tuner.tune()
    print("✅ Tuned thresholds:", result)
