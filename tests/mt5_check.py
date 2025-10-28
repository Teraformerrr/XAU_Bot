# D:\XAU_Bot\tests\mt5_check.py
import MetaTrader5 as mt5

# If your terminal path is not auto-detected, uncomment and set terminal64.exe path:
# mt5.initialize(path=r"C:\Program Files\MetaTrader 5\terminal64.exe")
print("init:", mt5.initialize())
print("terminal_info:", mt5.terminal_info())
print("account_info:", mt5.account_info())
print("last_error:", mt5.last_error())

SYMBOL = "XAUUSD"  # <-- change if needed to match Market Watch exactly
print("symbol_select:", mt5.symbol_select(SYMBOL, True))
print("tick:", mt5.symbol_info_tick(SYMBOL))
mt5.shutdown()
