from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Any

POST_URL_RE = re.compile(r"(?:https?://)?t\.me/(?:s/)?([A-Za-z0-9_]+)/([0-9]+)(?:\?.*)?$", re.IGNORECASE)


def parse_channel_post_reference(value: str) -> tuple[str, int] | None:
    """Parse a public t.me post URL; numeric IDs alone are not globally resolvable."""
    match = POST_URL_RE.fullmatch(value.strip())
    if not match:
        return None
    return match.group(1), int(match.group(2))


def root_message_id(messages: Iterable[Any], message_id: int) -> int:
    """Return the earliest message ID sharing the given Telegram album group ID."""
    items = list(messages)
    target = next((m for m in items if getattr(m, "id", None) == message_id), None)
    if target is None or getattr(target, "grouped_id", None) is None:
        return message_id
    group_id = target.grouped_id
    return min((int(m.id) for m in items if getattr(m, "grouped_id", None) == group_id), default=message_id)


def is_service_message(message: Any) -> bool:
    """Recognize service/update objects without depending on Telethon at import time."""
    if bool(getattr(message, "is_service", False)):
        return True
    class_name = type(message).__name__.lower()
    return class_name.endswith("messageservice") or class_name == "messageservice"
