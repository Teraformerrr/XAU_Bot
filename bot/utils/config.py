# D:\XAU_Bot\bot\utils\config.py
# ───────────────────────────────────────────────────────────────
#  Utility: YAML Config Loader
#  Safe load wrapper for configuration files.
# ───────────────────────────────────────────────────────────────

import yaml
from loguru import logger
from pathlib import Path


def load_yaml_config(path: str) -> dict:
    """
    Safely loads a YAML configuration file and returns a dictionary.
    If file is missing or malformed, returns an empty dict.
    """
    p = Path(path)
    if not p.exists():
        logger.warning(f"⚠️ Config file not found: {p}")
        return {}

    try:
        with p.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        logger.info(f"✅ YAML config loaded successfully from {p}")
        return data
    except Exception as e:
        logger.error(f"❌ Failed to read config file {p}: {e}")
        return {}
