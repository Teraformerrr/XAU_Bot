import logging
from bot.ai_core.ai_signal_activation import AISignalActivation
from bot.utils.config_loader import load_config

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")

if __name__ == "__main__":
    cfg = load_config("config.yaml")
    activator = AISignalActivation(cfg)
    result = activator.evaluate_and_execute("XAUUSD")
    print("\n🔍 Test Output →", result)
