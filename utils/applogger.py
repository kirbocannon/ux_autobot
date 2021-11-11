import os
import sys
import logging
from logging.config import dictConfig
from pathlib import Path

PARENT_PATH = Path(os.path.abspath(__file__)).parent.parent

LOG_DIRECTORY = f"{str(PARENT_PATH)}/logs"
REPORTS_DIRECTORY = f"{str(PARENT_PATH)}/reports"


logging_config = dict(
    version=1,
    formatters={
        "verbose": {
            "format": (
                "[%(asctime)s] %(levelname)s " "[%(name)s:%(lineno)s] %(message)s"
            ),
            "datefmt": "%d/%b/%Y %H:%M:%S",
        },
        "simple": {
            "format": "%(levelname)s %(message)s",
        },
        "just-the-message": {"format": "%(message)s"},
    },
    handlers={
        "apptest-logger": {
            "class": "logging.handlers.RotatingFileHandler",
            "formatter": "verbose",
            "level": logging.DEBUG,
            "filename": f"{LOG_DIRECTORY}/apptest.log",
            "maxBytes": 52428800,
            "backupCount": 10,
        },
        "report-logger": {
            "class": "logging.handlers.RotatingFileHandler",
            "formatter": "just-the-message",
            "level": logging.DEBUG,
            "filename": f"{REPORTS_DIRECTORY}/reports.txt",
            "maxBytes": 52428800,
            "backupCount": 50,
        },
        "console": {
            "class": "logging.StreamHandler",
            "level": "DEBUG",
            "formatter": "simple",
            "stream": sys.stdout,
        },
    },
    loggers={
        "apptest_logger": {
            "handlers": ["apptest-logger", "console"],
            "level": logging.DEBUG,
        },
        "report_logger": {"handlers": ["report-logger"], "level": logging.DEBUG},
    },
)

dictConfig(logging_config)

apptest_logger = logging.getLogger("apptest_logger")
report_logger = logging.getLogger("report_logger")
