import logging
from bot.execution.mt5_exec_simple import MT5ExecSimple

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s | %(levelname)-8s | %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S")

if __name__ == "__main__":
    bot = MT5ExecSimple(symbol="XAUUSD.sd", lot=0.01)
    if bot.connect():
        bot.trade("BUY")   # try "SELL" later
        bot.close()
