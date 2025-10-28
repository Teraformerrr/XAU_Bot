import logging
import json
from logging.handlers import RotatingFileHandler

def configure_logger(name: str, logfile: str = "reports/system_log.jsonl"):
    """
    Configure a structured JSON logger for consistent logging across modules.
    Automatically creates file if not exists.
    """
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger  # Already configured

    logger.setLevel(logging.INFO)

    # JSON formatter
    class JsonFormatter(logging.Formatter):
        def format(self, record):
            log_record = {
                "level": record.levelname,
                "name": record.name,
                "message": record.getMessage(),
            }
            return json.dumps(log_record)

    handler = RotatingFileHandler(logfile, maxBytes=2_000_000, backupCount=3)
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)

    # Stream to console too
    console = logging.StreamHandler()
    console.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
    logger.addHandler(console)

    return logger
