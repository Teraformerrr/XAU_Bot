from bot.scheduler.vol_sync import VolatilitySynchronizer
import time

if __name__ == "__main__":
    sync = VolatilitySynchronizer()
    sync.update("XAUUSD", 0.2135)
    print("Initial:", sync.read())
    time.sleep(2)
    print("Retrieved:", sync.get_volatility())
