from __future__ import annotations

import asyncio
import logging
from collections import deque
from datetime import datetime
from typing import Any

import aiohttp

from app.config import Settings
from app.logger import sanitize
from app.rate_limiter import RateLimiter
from app.storage import JsonStorage


class Engine:
    def __init__(self, settings: Settings, storage: JsonStorage) -> None:
        self.settings = settings
        self.storage = storage
        self.limiter = RateLimiter(settings.min_request_delay)
        self._subscribers: set[asyncio.Queue[dict[str, Any]]] = set()
        self._logs: deque[str] = deque(maxlen=300)
        self.logger = logging.getLogger("orchestrator")

    def publish(self, event: dict[str, Any]) -> None:
        for queue in tuple(self._subscribers):
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                try:
                    queue.get_nowait()
                    queue.put_nowait(event)
                except (asyncio.QueueEmpty, asyncio.QueueFull):
                    pass

    def log(self, message: str, level: str = "info") -> None:
        clean = sanitize(message)
        self._logs.append(clean)
        getattr(self.logger, level, self.logger.info)(clean)
        self.publish({"type": "log", "message": clean})

    def snapshot(self) -> dict[str, Any]:
        return {
            **self.storage.load(),
            "status": {
                "web": "online",
                "control_bot_configured": bool(self.settings.ctrl_bot_token),
                "proxy_configured": bool(self.settings.proxy_host and self.settings.proxy_port),
                "seconds_until_slot": round(self.limiter.seconds_until_slot(), 1),
                "pin_enabled": bool(self.settings.web_pin),
            },
            "logs": list(self._logs),
        }

    async def subscribe(self) -> asyncio.Queue[dict[str, Any]]:
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=100)
        self._subscribers.add(queue)
        await queue.put({"type": "snapshot", "data": self.snapshot()})
        return queue

    def unsubscribe(self, queue: asyncio.Queue[dict[str, Any]]) -> None:
        self._subscribers.discard(queue)

    def add_channel(self, channel_id: str, title: str) -> dict[str, Any]:
        record = {"id": self.storage.validate_channel_id(channel_id),
                  "title": self.storage.validate_name(title, "Title"), "added_at": datetime.now().isoformat(timespec="seconds")}
        self.storage.add_channel(record)
        self.log(f"Channel metadata added: {record['title']}")
        self.publish({"type": "state", "data": self.snapshot()})
        return record

    def add_bot(self, username: str, channel_id: str, note: str = "") -> dict[str, Any]:
        username = self.storage.validate_name(username.lstrip("@"), "Username")
        channel_id = self.storage.validate_channel_id(channel_id)
        if not any(ch["id"] == channel_id for ch in self.storage.load()["channels"]):
            raise ValueError("Add the channel to inventory first")
        bot = {"username": username, "channel_id": channel_id,
               "note": self.storage.validate_name(note, "Note") if note else "", "status": "unverified"}
        self.storage.add_bot(bot)
        self.log(f"Bot metadata added: @{username}")
        self.publish({"type": "state", "data": self.snapshot()})
        return bot

    def delete(self, collection: str, item_id: str) -> bool:
        deleted = self.storage.delete(collection, item_id)
        if deleted:
            self.log(f"Removed {collection} entry: {item_id}")
            self.publish({"type": "state", "data": self.snapshot()})
        return deleted

    async def diagnose_control_bot(self) -> dict[str, Any]:
        if not self.settings.ctrl_bot_token:
            raise ValueError("CTRL_BOT_TOKEN is not configured")
        await self.limiter.wait_turn()
        timeout = aiohttp.ClientTimeout(total=15)
        connector = None
        if self.settings.proxy_host and self.settings.proxy_port:
            from aiohttp_socks import ProxyConnector, ProxyType
            connector = ProxyConnector(proxy_type=ProxyType.SOCKS5, host=self.settings.proxy_host,
                                       port=self.settings.proxy_port, username=self.settings.proxy_user or None,
                                       password=self.settings.proxy_pass or None, rdns=True)
        url = f"https://api.telegram.org/bot{self.settings.ctrl_bot_token}/getMe"
        try:
            async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
                async with session.get(url) as response:
                    body = await response.json(content_type=None)
                    if response.status != 200 or not body.get("ok"):
                        raise ValueError(f"Telegram Bot API returned HTTP {response.status}")
                    result = body.get("result", {})
                    username = sanitize(result.get("username", "unknown"))
                    self.log(f"Control Bot API diagnostics succeeded for @{username}")
                    return {"ok": True, "username": username, "id": result.get("id")}
        except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
            self.log(f"Bot API diagnostics failed: {type(exc).__name__}", "warning")
            raise ValueError("Bot API connection failed; check network/proxy settings") from exc
