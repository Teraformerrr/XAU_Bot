from bot.engines.ai_signal_router import AISignalRouter
import random

if __name__ == "__main__":
    router = AISignalRouter(use_lstm=False)
    for i in range(10):
        fake_features = {"EMA_20": random.random(), "RSI_14": random.random()}
        volatility = random.uniform(0.02, 0.25)
        result = router.decide_action(fake_features, volatility)
        print(f"{i:02d} | conf={result['confidence']:.3f} | vol={result['volatility']:.3f} → {result['action']}")
