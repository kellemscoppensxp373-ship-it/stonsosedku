from __future__ import annotations

import logging
import re
from collections.abc import Callable
from pathlib import Path

TOKEN_RE = re.compile(r"\b\d{8,12}:[A-Za-z0-9_-]{30,60}\b")
WINDOW_PATH_RE = re.compile(r"(?i)(?:[A-Z]:\\Users\\)[^\\\s]+(?:\\[^\s]*)?")
HASH_RE = re.compile(r"(?i)(api[_ -]?hash\s*[:=]\s*)[A-Fa-f0-9]{20,}")


def sanitize(text: object) -> str:
    value = str(text)
    value = TOKEN_RE.sub("***REDACTED***", value)
    value = WINDOW_PATH_RE.sub("***REDACTED***", value)
    value = HASH_RE.sub(r"\1***REDACTED***", value)
    return value


class SafeFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        return sanitize(super().format(record))


class EventLogHandler(logging.Handler):
    def __init__(self, publish: Callable[[str], None] | None = None) -> None:
        super().__init__()
        self.publish = publish

    def emit(self, record: logging.LogRecord) -> None:
        line = sanitize(self.format(record))
        if self.publish:
            self.publish(line)


def configure_logging(logs_dir: Path, publish: Callable[[str], None] | None = None) -> logging.Logger:
    logs_dir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("orchestrator")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    formatter = SafeFormatter("%(asctime)s | %(levelname)s | %(message)s")
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    disk = logging.FileHandler(logs_dir / "app.log", encoding="utf-8")
    disk.setFormatter(formatter)
    stream = EventLogHandler(publish)
    stream.setFormatter(formatter)
    logger.addHandler(console)
    logger.addHandler(disk)
    logger.addHandler(stream)
    return logger
