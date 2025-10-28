# D:\XAU_Bot\bot\core\session_logger.py
import logging
import os
from datetime import datetime

class SessionLogger:
    _instance = None  # Singleton instance

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SessionLogger, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        # Ensure directory exists
        os.makedirs("reports/logs", exist_ok=True)

        # Configure logger
        self.logger = logging.getLogger("session")
        if not self.logger.handlers:
            handler = logging.FileHandler("reports/logs/session.log", encoding="utf-8")
            formatter = logging.Formatter(
                "%(asctime)s | %(levelname)s | %(message)s", "%Y-%m-%d %H:%M:%S"
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

        # Session started
        self.log_event("SESSION_START", "🚀 New trading session started")

    def log_event(self, event_type, message, *args):
        """
        Logs both to console and file.
        Handles optional arguments (e.g. exceptions, dicts, or debug data).
        """
        # Build full message
        extra = " | ".join(str(a) for a in args) if args else ""
        full_message = f"{message} | {extra}" if extra else message

        # Print to console with clear format
        print(f"{event_type} | {full_message}")

        # Save to file
        self.logger.info(f"{event_type} | {full_message}")

    def log_error(self, event_type, message, error):
        """Dedicated method for logging errors with traceback-style output."""
        error_text = f"{message} | ERROR: {error}"
        print(f"{event_type} ❌ | {error_text}")
        self.logger.error(f"{event_type} | {error_text}")
