from pathlib import Path

test_path = Path(r"D:\XAU_Bot\data\trade_log.csv")
print("✅ Absolute Path:", test_path)
print("📁 Exists:", test_path.exists())

# Show working directory
import os
print("📂 Current Working Directory:", os.getcwd())
