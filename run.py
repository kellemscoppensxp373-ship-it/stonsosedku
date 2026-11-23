from __future__ import annotations

import asyncio
import logging
import os
import sys
from pathlib import Path

import uvicorn

from app.config import load_settings
from app.engine import Engine
from app.logger import configure_logging
from app.storage import JsonStorage
from app.web_server import create_app


class InstanceLock:
    """Cross-platform non-blocking process lock held for the lifetime of the server."""
    def __init__(self, path: Path) -> None:
        self.path = path
        self.file = None

    def acquire(self) -> bool:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.file = self.path.open("a+b")
        try:
            if os.name == "nt":
                import msvcrt
                self.file.seek(0)
                if self.file.read(1) == b"":
                    self.file.write(b"0")
                    self.file.flush()
                self.file.seek(0)
                msvcrt.locking(self.file.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            return True
        except (OSError, BlockingIOError):
            self.file.close()
            self.file = None
            return False

    def release(self) -> None:
        if not self.file:
            return
        try:
            if os.name == "nt":
                import msvcrt
                self.file.seek(0)
                msvcrt.locking(self.file.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.file.fileno(), fcntl.LOCK_UN)
        finally:
            self.file.close()
            self.file = None


def main() -> int:
    try:
        settings = load_settings()
    except ValueError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2
    lock = InstanceLock(settings.data_dir / "orchestrator.lock")
    if not lock.acquire():
        print("Another instance is already running.", file=sys.stderr)
        return 3
    engine = Engine(settings, JsonStorage(settings.data_dir / "state.json"))
    configure_logging(settings.logs_dir, publish=lambda line: engine.publish({"type": "log", "message": line}))
    engine.log("Local dashboard started; remote network actions are disabled except explicit getMe diagnostics.")
    config = uvicorn.Config(create_app(settings, engine), host=settings.web_host, port=settings.web_port,
                            log_level="warning", access_log=False)
    try:
        asyncio.run(uvicorn.Server(config).serve())
    except KeyboardInterrupt:
        pass
    finally:
        lock.release()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
