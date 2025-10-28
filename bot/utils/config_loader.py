import yaml
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

def load_config(path: str = "config.yaml") -> dict:
    """
    Loads a YAML configuration file and returns it as a Python dict.
    If loading fails, returns a safe default configuration.
    """
    config_path = Path(path)

    if not config_path.exists():
        logger.warning("⚠️ Config file %s not found. Using defaults.", path)
        return _default_config()

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            logger.info("✅ YAML config loaded successfully from %s", path)
            return data or _default_config()
    except Exception as e:
        logger.error("⚠️ Could not load YAML config (%s); using defaults.", e)
        return _default_config()


def _default_config() -> dict:
    """Fallback default configuration when config.yaml is missing or broken."""
    return {
        "mode": "paper",
        "start_equity": 100000,
        "engine": {
            "min_confidence": 0.55,
            "bar_seconds": 60,
            "max_open_positions": 3,
            "cool_down_bars": 5,
        },
        "risk": {
            "max_dd_pct": 20.0,
            "max_risk_per_trade_pct": 2.0,
        },
        "symbols": {
            "metals": ["XAUUSD"],
        },
    }
