import json
import logging
from datetime import datetime, timezone


def _get_correlation_id() -> str | None:
    """Safely get correlation ID, returning None if not available."""
    try:
        from core.correlation_middleware import get_correlation_id

        return get_correlation_id()
    except ImportError:
        return None


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add correlation ID if available
        correlation_id = _get_correlation_id()
        if correlation_id:
            log_entry["correlation_id"] = correlation_id

        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
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
    if json_format:
        return logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    return logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(lineno)d - %(message)s"
    )


def get_file_formatter(json_format: bool) -> logging.Formatter:
    if json_format:
        return JSONFormatter()
    return logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(lineno)d - %(message)s"
    )
