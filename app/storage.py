from __future__ import annotations

import json
import os
import re
import tempfile
import threading
from pathlib import Path
from typing import Any

NAME_RE = re.compile(r"^[\w .@+-]{1,80}$", re.UNICODE)


def empty_state() -> dict[str, Any]:
    return {"version": 1, "channels": [], "bots": []}


class JsonStorage:
    """Atomic local JSON metadata store. It deliberately does not store bot tokens."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = threading.RLock()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.save(empty_state())

    def load(self) -> dict[str, Any]:
        with self._lock:
            try:
                raw = json.loads(self.path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                return empty_state()
            if not isinstance(raw, dict) or raw.get("version") != 1:
                return empty_state()
            raw.setdefault("channels", [])
            raw.setdefault("bots", [])
            return raw

    def save(self, state: dict[str, Any]) -> None:
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            fd, tmp_name = tempfile.mkstemp(prefix=self.path.name, suffix=".tmp", dir=self.path.parent)
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as tmp:
                    json.dump(state, tmp, ensure_ascii=False, indent=2)
                    tmp.flush()
                    os.fsync(tmp.fileno())
                os.replace(tmp_name, self.path)
            finally:
                if os.path.exists(tmp_name):
                    os.unlink(tmp_name)

    def add_channel(self, channel: dict[str, Any]) -> dict[str, Any]:
        state = self.load()
        if any(c["id"] == channel["id"] for c in state["channels"]):
            raise ValueError("Channel already exists")
        state["channels"].append(channel)
        self.save(state)
        return channel

    def add_bot(self, bot: dict[str, Any]) -> dict[str, Any]:
        if "token" in bot or "api_token" in bot:
            raise ValueError("Bot tokens are not accepted or stored")
        state = self.load()
        if any(b["username"].lower() == bot["username"].lower() for b in state["bots"]):
            raise ValueError("Bot username already exists")
        state["bots"].append(bot)
        self.save(state)
        return bot

    def delete(self, collection: str, item_id: str) -> bool:
        if collection not in {"channels", "bots"}:
            raise ValueError("Unknown collection")
        state = self.load()
        key = "id" if collection == "channels" else "username"
        prior = len(state[collection])
        state[collection] = [item for item in state[collection] if str(item.get(key)) != item_id]
        if len(state[collection]) == prior:
            return False
        self.save(state)
        return True

    @staticmethod
    def validate_channel_id(value: str) -> str:
        value = value.strip()
        if not value or len(value) > 128:
            raise ValueError("Channel ID or username is required (max 128 characters)")
        return value

    @staticmethod
    def validate_name(value: str, label: str = "Name") -> str:
        value = value.strip()
        if not NAME_RE.fullmatch(value):
            raise ValueError(f"{label} must be 1-80 characters")
        return value
