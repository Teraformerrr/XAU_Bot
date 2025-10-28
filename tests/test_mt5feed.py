from bot.data_feed import MT5Feed

feed = MT5Feed("D:/XAU_Bot/config.yaml")
df = feed.snapshot_symbol("XAUUSD")   # or XAUUSD.sd if that’s your broker suffix

print("Data shape:", df.shape)
print(df.head())
