import logging
import os
from logging.handlers import RotatingFileHandler

from pythonjsonlogger import jsonlogger

from bot.core.correlation import get_correlation_id

_logging_configured = False


class CorrelationJsonFormatter(jsonlogger.JsonFormatter):
    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict)
        log_record["correlation_id"] = get_correlation_id()
        log_record["service"] = "trading_bot"

    def format(self, record):
        record.timestamp = self.formatTime(record, self.datefmt)
        record.level = record.levelname
        return super().format(record)


def setup_logging(log_level: str = "INFO", log_dir: str = "logs") -> None:
    global _logging_configured
    if _logging_configured:
        return

    os.makedirs(log_dir, exist_ok=True)

    root = logging.getLogger()
    root.setLevel(log_level)
    root.handlers.clear()

    # File handler — structured JSON
    json_handler = RotatingFileHandler(
        os.path.join(log_dir, "app.log"),
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    json_handler.setLevel(log_level)
    json_handler.setFormatter(
        CorrelationJsonFormatter("%(timestamp)s %(level)s %(name)s %(message)s")
    )
    root.addHandler(json_handler)

    # Suppress noisy third-party loggers
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("binance").setLevel(logging.WARNING)

    _logging_configured = True
