import os
import json
import time
import traceback
from datetime import datetime
import MetaTrader5 as mt5
from bot.core.session_logger import SessionLogger


class SafeExecutor:
    """
    Wraps any function call with automatic retry, MT5 reconnect,
    exponential backoff, and structured error logging.
    """

    def __init__(self, max_retries: int = 3, base_delay: int = 5):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.logger = SessionLogger()
        os.makedirs("reports/logs", exist_ok=True)
        self.error_log = "reports/logs/error_log.jsonl"

    def _reconnect_mt5(self):
        """Force MT5 reinitialization if disconnected."""
        try:
            if not mt5.initialize():
                self.logger.log_event("MT5_RECONNECT_FAIL", str(mt5.last_error()))
                return False
            self.logger.log_event("MT5_RECONNECT_OK", "Reconnected to MetaTrader 5")
            return True
        except Exception as e:
            self.logger.log_event("MT5_RECONNECT_EXCEPTION", str(e))
            return False

    def _write_error(self, error_entry: dict):
        """Append structured error entry to log file."""
        try:
            with open(self.error_log, "a", encoding="utf-8") as f:
                f.write(json.dumps(error_entry, ensure_ascii=False) + "\n")
        except Exception:
            # never break because of logging
            pass

    def run_safe(self, fn, *args, **kwargs):
        """
        Run fn() with safe retry and backoff.
        Returns fn()’s result or None if all retries fail.
        """
        for attempt in range(1, self.max_retries + 1):
            try:
                result = fn(*args, **kwargs)
                return result

            except Exception as e:
                delay = self.base_delay * (3 ** (attempt - 1))
                tb = traceback.format_exc()
                msg = f"Attempt {attempt}/{self.max_retries} failed — retrying in {delay}s"
                self.logger.log_event("ERROR", msg)
                self._write_error({
                    "timestamp": datetime.now().isoformat(),
                    "attempt": attempt,
                    "error": str(e),
                    "traceback": tb,
                })

                # Try to reconnect MT5 on first two failures
                if attempt < self.max_retries:
                    self._reconnect_mt5()
                    time.sleep(delay)
                else:
                    self.logger.log_event("FATAL", "All retries failed — skipping cycle")
                    return None
