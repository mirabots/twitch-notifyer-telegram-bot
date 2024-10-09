import getopt
import logging
import sys
from types import SimpleNamespace

from litestar.logging import LoggingConfig

# levelDEBUG = logging.INFO
levelDEBUG = logging.DEBUG
levelINFO = logging.INFO
FORMAT = "%(levelname)-8s\t%(asctime)s\t\t%(message)s"


def get_args() -> SimpleNamespace:
    args = SimpleNamespace(env="dev", host="0.0.0.0", port=8880)
    opts, _ = getopt.getopt(sys.argv[1:], "H:P:E:", ["host=", "port=", "env="])
    for name, value in opts:
        if name in ("-H", "--host"):
            args.host = value
        if name in ("-P", "--port"):
            args.port = int(value)
        if name in ("-E", "--env"):
            args.env = value
    return args


def get_logger(level: int) -> logging.Logger:
    logger = logging.getLogger()
    logging.basicConfig(format=FORMAT, level=level)
    return logger


def get_logging_config(level: int) -> LoggingConfig:
    return LoggingConfig(
        root={"level": logging.getLevelName(level), "handlers": ["console"]},
        formatters={"standard": {"format": FORMAT}},
    )


def disable_unnecessary_loggers() -> None:
    urllib3_logger = logging.getLogger("urllib3")
    urllib3_logger.setLevel(logging.CRITICAL)

    httpx_logger = logging.getLogger("httpx")
    httpx_logger.setLevel(logging.CRITICAL)

    aiogram_event_logger = logging.getLogger("aiogram.event")
    aiogram_event_logger.setLevel(logging.CRITICAL)
