# D:\XAU_Bot\bot\utils\config.py
import yaml
import logging
from pathlib import Path

log = logging.getLogger("bot.utils.config")

def load_config(path: str = "config.yaml"):
    """
    Loads YAML config safely (UTF-8 only).
    Falls back to defaults if file missing or unreadable.
    """
    config_path = Path(path)
    if not config_path.exists():
        log.warning("⚠️ Config file not found at %s — using defaults.", path)
        return {
            "mode": "paper",
            "engine": {
                "interval_sec": 60,
                "buy_threshold": 0.555,
                "sell_threshold": 0.445,
            },
        }

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
        log.info("✅ YAML config loaded successfully from %s", path)
        return cfg
    except UnicodeDecodeError:
        log.error("❌ Config not UTF-8 encoded! Please re-save with UTF-8 encoding.")
        raise
    except Exception as e:
        log.exception("❌ Failed to load YAML config (%s); using defaults.", e)
        return {
            "mode": "paper",
            "engine": {
                "interval_sec": 60,
                "buy_threshold": 0.555,
                "sell_threshold": 0.445,
            },
        }
