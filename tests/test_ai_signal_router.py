import logging
from bot.engines.ai_signal_router import AISignalRouter
logging.basicConfig(level=logging.INFO)

if __name__ == "__main__":
    r = AISignalRouter()
    print("Signal →", r.get_signal())
