from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Settings:
    admin_id: int
    ctrl_bot_token: str
    min_request_delay: float
    web_host: str
    web_port: int
    web_pin: str
    proxy_host: str
    proxy_port: int | None
    proxy_user: str
    proxy_pass: str
    data_dir: Path
    logs_dir: Path


def load_settings(env_file: Path | None = None) -> Settings:
    load_dotenv(env_file or ROOT_DIR / ".env", override=False)
    try:
        admin_id = int(os.getenv("ADMIN_ID", "0"))
        delay = float(os.getenv("MIN_REQUEST_DELAY", "15"))
        port = int(os.getenv("WEB_PORT", "8080"))
        proxy_port_raw = os.getenv("PROXY_PORT", "").strip()
        proxy_port = int(proxy_port_raw) if proxy_port_raw else None
    except ValueError as exc:
        raise ValueError("ADMIN_ID, MIN_REQUEST_DELAY, WEB_PORT and PROXY_PORT must be numeric") from exc
    host = os.getenv("WEB_HOST", "127.0.0.1").strip()
    if not 1 <= port <= 65535:
        raise ValueError("WEB_PORT must be between 1 and 65535")
    if delay < 0:
        raise ValueError("MIN_REQUEST_DELAY cannot be negative")
    if proxy_port is not None and not 1 <= proxy_port <= 65535:
        raise ValueError("PROXY_PORT must be between 1 and 65535")
    if host not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError("WEB_HOST must be a loopback address; remote access is intentionally disabled")
    return Settings(
        admin_id=admin_id,
        ctrl_bot_token=os.getenv("CTRL_BOT_TOKEN", "").strip(),
        min_request_delay=delay,
        web_host=host,
        web_port=port,
        web_pin=os.getenv("WEB_PIN", ""),
        proxy_host=os.getenv("PROXY_HOST", "").strip(),
        proxy_port=proxy_port,
        proxy_user=os.getenv("PROXY_USER", ""),
        proxy_pass=os.getenv("PROXY_PASS", ""),
        data_dir=ROOT_DIR / "data",
        logs_dir=ROOT_DIR / "logs",
    )
