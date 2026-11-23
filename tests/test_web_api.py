from fastapi.testclient import TestClient

from app.config import Settings
from app.engine import Engine
from app.storage import JsonStorage
from app.web_server import create_app


def make_settings(tmp_path, pin="secret-pin"):
    return Settings(admin_id=123, ctrl_bot_token="", min_request_delay=0, web_host="127.0.0.1",
                    web_port=8080, web_pin=pin, proxy_host="", proxy_port=None, proxy_user="", proxy_pass="",
                    data_dir=tmp_path / "data", logs_dir=tmp_path / "logs")


def test_pin_protects_state_and_crud_syncs_snapshot(tmp_path):
    settings = make_settings(tmp_path)
    engine = Engine(settings, JsonStorage(settings.data_dir / "state.json"))
    client = TestClient(create_app(settings, engine))
    assert client.get("/api/state").status_code == 401
    headers = {"X-Web-PIN": "secret-pin"}
    response = client.post("/api/channels", json={"id": "@demo", "title": "Demo"}, headers=headers)
    assert response.status_code == 201
    assert client.post("/api/bots", json={"username": "worker_bot", "channel_id": "@demo"}, headers=headers).status_code == 201
    state = client.get("/api/state", headers=headers).json()
    assert state["channels"][0]["id"] == "@demo"
    assert state["bots"][0]["username"] == "worker_bot"
    assert client.delete("/api/bots/worker_bot", headers=headers).json() == {"deleted": True}


def test_tokens_are_rejected_and_websocket_requires_pin(tmp_path):
    settings = make_settings(tmp_path)
    client = TestClient(create_app(settings, Engine(settings, JsonStorage(settings.data_dir / "state.json"))))
    headers = {"X-Web-PIN": "secret-pin"}
    client.post("/api/channels", json={"id": "@demo", "title": "Demo"}, headers=headers)
    rejected = client.post("/api/bots", json={"username": "x", "channel_id": "@demo", "token": "should-not-be-accepted"}, headers=headers)
    assert rejected.status_code == 422
    with client.websocket_connect("/ws?pin=secret-pin") as websocket:
        event = websocket.receive_json()
        assert event["type"] == "snapshot"
        assert event["data"]["channels"][0]["id"] == "@demo"
