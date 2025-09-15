import json
import logging
import logging.handlers
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


class SecurityEvent:
    AUTH_LOGIN_SUCCESS = "auth.login.success"
    AUTH_LOGIN_FAILURE = "auth.login.failure"
    AUTH_LOGOUT = "auth.logout"
    AUTH_REGISTER = "auth.register"
    AUTH_SESSION_EXPIRED = "auth.session.expired"
    AUTH_ACCOUNT_DELETED = "auth.account.deleted"

    ADMIN_USER_CREATE = "admin.user.create"
    ADMIN_USER_UPDATE = "admin.user.update"
    ADMIN_USER_DELETE = "admin.user.delete"
    ADMIN_POLL_CREATE = "admin.poll.create"
    ADMIN_POLL_DELETE = "admin.poll.delete"
    ADMIN_RESULT_ENTRY = "admin.result.entry"
    ADMIN_RESULT_UPDATE = "admin.result.update"
    ADMIN_RESULT_DELETE = "admin.result.delete"

    POLL_VOTE_CAST = "poll.vote.cast"
    POLL_VOTE_UPDATE = "poll.vote.update"
    POLL_VOTE_DELETE = "poll.vote.delete"

    DB_ERROR = "database.error"
    DB_TIMEOUT = "database.timeout"
    DB_CONNECTION_FAILED = "database.connection.failed"

    ACCESS_DENIED = "security.access.denied"
    SUSPICIOUS_ACTIVITY = "security.suspicious.activity"
    RATE_LIMIT_EXCEEDED = "security.rate.limit.exceeded"


class JSONFormatter(logging.Formatter):
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


class SABCLogger:
    def __init__(self, log_dir: str = "logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        self._configured = False

    def configure_logging(
        self,
        log_level: str = "INFO",
        json_format: bool = True,
        max_bytes: int = 10 * 1024 * 1024,  # 10MB
        backup_count: int = 5,
    ) -> None:
        if self._configured:
            return

        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        numeric_level = getattr(logging, log_level.upper(), logging.INFO)
        root_logger.setLevel(numeric_level)

        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(numeric_level)
        app_handler = logging.handlers.RotatingFileHandler(
            self.log_dir / "sabc.log", maxBytes=max_bytes, backupCount=backup_count
        )
        app_handler.setLevel(numeric_level)

        security_handler = logging.handlers.RotatingFileHandler(
            self.log_dir / "security.log", maxBytes=max_bytes, backupCount=backup_count
        )
        security_handler.setLevel(logging.INFO)

        error_handler = logging.handlers.RotatingFileHandler(
            self.log_dir / "error.log", maxBytes=max_bytes, backupCount=backup_count
        )
        error_handler.setLevel(logging.ERROR)

        formatter: logging.Formatter
        if json_format:
            formatter = JSONFormatter()
            console_formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            console_handler.setFormatter(console_formatter)
        else:
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(lineno)d - %(message)s"
            )
            console_handler.setFormatter(formatter)

        app_handler.setFormatter(formatter)
        security_handler.setFormatter(formatter)
        error_handler.setFormatter(formatter)

        root_logger.addHandler(console_handler)
        root_logger.addHandler(app_handler)
        root_logger.addHandler(error_handler)

        security_logger = logging.getLogger("sabc.security")
        security_logger.addHandler(security_handler)
        security_logger.propagate = False  # Don't duplicate to root logger

        self._configured = True

        logger = logging.getLogger(__name__)
        logger.info(
            "Logging system initialized",
            extra={
                "log_level": log_level,
                "json_format": json_format,
                "log_dir": str(self.log_dir),
            },
        )

    def get_logger(self, name: str) -> logging.Logger:
        if not self._configured:
            self.configure_logging()
        return logging.getLogger(f"sabc.{name}")

    def log_security_event(
        self,
        event_type: str,
        user_id: Optional[int] = None,
        user_email: Optional[str] = None,
        ip_address: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        level: int = logging.INFO,
    ) -> None:
        if not self._configured:
            self.configure_logging()

        security_logger = logging.getLogger("sabc.security")

        extra = {
            "event_type": event_type,
            "user_id": user_id,
            "user_email": user_email,
            "ip_address": ip_address,
            "details": details or {},
        }

        security_logger.log(level, f"Security event: {event_type}", extra=extra)


sabc_logger = SABCLogger()


def get_logger(name: str) -> logging.Logger:
    return sabc_logger.get_logger(name)


def log_security_event(
    event_type: str,
    user_id: Optional[int] = None,
    user_email: Optional[str] = None,
    ip_address: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    level: int = logging.INFO,
) -> None:
    sabc_logger.log_security_event(event_type, user_id, user_email, ip_address, details, level)


def configure_logging(log_level: str = "INFO", json_format: bool = True) -> None:
    sabc_logger.configure_logging(log_level, json_format)
