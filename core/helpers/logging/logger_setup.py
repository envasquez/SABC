import logging


def configure_root_logger(numeric_level: int) -> logging.Logger:
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    root_logger.setLevel(numeric_level)
    return root_logger


def configure_security_logger(security_handler: logging.Handler) -> logging.Logger:
    security_logger = logging.getLogger("sabc.security")
    security_logger.addHandler(security_handler)
    security_logger.propagate = False
    return security_logger
