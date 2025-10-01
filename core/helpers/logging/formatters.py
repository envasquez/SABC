import json
import logging
from datetime import datetime


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging output."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        # Add custom fields from extra parameter
        for key, value in record.__dict__.items():
            if key not in (
                "name",
                "msg",
                "args",
                "levelname",
                "levelno",
                "pathname",
                "filename",
                "module",
                "lineno",
                "funcName",
                "created",
                "msecs",
                "relativeCreated",
                "thread",
                "threadName",
                "processName",
                "process",
                "exc_info",
                "exc_text",
                "stack_info",
            ):
                log_entry[key] = value

        return json.dumps(log_entry, default=str, ensure_ascii=False)


def get_console_formatter(json_format: bool) -> logging.Formatter:
    """Get appropriate console formatter based on format preference."""
    if json_format:
        return logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    else:
        return logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(lineno)d - %(message)s"
        )


def get_file_formatter(json_format: bool) -> logging.Formatter:
    """Get appropriate file formatter based on format preference."""
    if json_format:
        return JSONFormatter()
    else:
        return logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(lineno)d - %(message)s"
        )
