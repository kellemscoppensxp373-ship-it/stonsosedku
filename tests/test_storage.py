import json

import pytest

from app.storage import JsonStorage


def test_atomic_json_storage_roundtrip_and_temp_cleanup(tmp_path):
    path = tmp_path / "data" / "state.json"
    store = JsonStorage(path)
    store.add_channel({"id": "-100123", "title": "Demo"})
    assert json.loads(path.read_text(encoding="utf-8"))["channels"][0]["title"] == "Demo"
    assert list(path.parent.glob("*.tmp")) == []


def test_duplicate_items_rejected_and_delete_is_precise(tmp_path):
    store = JsonStorage(tmp_path / "state.json")
    store.add_channel({"id": "@demo", "title": "Demo"})
    with pytest.raises(ValueError):
        store.add_channel({"id": "@demo", "title": "Copy"})
    store.add_bot({"username": "helper_bot", "channel_id": "@demo", "status": "unverified"})
    assert store.delete("bots", "helper_bot")
    assert not store.delete("bots", "helper_bot")


def test_bot_token_is_never_accepted(tmp_path):
    store = JsonStorage(tmp_path / "state.json")
    with pytest.raises(ValueError, match="not accepted"):
        store.add_bot({"username": "worker_bot", "token": "sensitive"})
    assert store.load()["bots"] == []
