from __future__ import annotations

import hmac
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Header, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field

from app.config import Settings, load_settings
from app.engine import Engine
from app.storage import JsonStorage

WEB_DIR = Path(__file__).resolve().parent.parent / "web"


class ChannelInput(BaseModel):
    id: str = Field(min_length=1, max_length=128)
    title: str = Field(min_length=1, max_length=80)


class BotInput(BaseModel):
    username: str = Field(min_length=1, max_length=80)
    channel_id: str = Field(min_length=1, max_length=128)
    note: str = Field(default="", max_length=80)

    model_config = ConfigDict(extra="forbid")


def create_app(settings: Settings | None = None, engine: Engine | None = None) -> FastAPI:
    settings = settings or load_settings()
    engine = engine or Engine(settings, JsonStorage(settings.data_dir / "state.json"))
    app = FastAPI(title="Telegram Bot Inventory", docs_url=None, redoc_url=None)
    app.state.engine = engine
    app.state.settings = settings

    def authorize(pin: str | None) -> None:
        if settings.web_pin and not hmac.compare_digest(pin or "", settings.web_pin):
            raise HTTPException(status_code=401, detail="Invalid or missing dashboard PIN")

    @app.get("/")
    async def index() -> FileResponse:
        return FileResponse(WEB_DIR / "index.html")

    @app.get("/styles.css")
    async def styles() -> FileResponse:
        return FileResponse(WEB_DIR / "styles.css", media_type="text/css")

    @app.get("/app.js")
    async def script() -> FileResponse:
        return FileResponse(WEB_DIR / "app.js", media_type="application/javascript")

    @app.get("/api/state")
    async def state(x_web_pin: str | None = Header(default=None)) -> dict[str, Any]:
        authorize(x_web_pin)
        return engine.snapshot()

    @app.post("/api/channels", status_code=201)
    async def add_channel(payload: ChannelInput, x_web_pin: str | None = Header(default=None)) -> dict[str, Any]:
        authorize(x_web_pin)
        try:
            return engine.add_channel(payload.id, payload.title)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/bots", status_code=201)
    async def add_bot(payload: BotInput, x_web_pin: str | None = Header(default=None)) -> dict[str, Any]:
        authorize(x_web_pin)
        try:
            return engine.add_bot(payload.username, payload.channel_id, payload.note)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.delete("/api/{collection}/{item_id}")
    async def delete_item(collection: str, item_id: str,
                          x_web_pin: str | None = Header(default=None)) -> dict[str, bool]:
        authorize(x_web_pin)
        if collection not in {"channels", "bots"}:
            raise HTTPException(status_code=404, detail="Unknown collection")
        if not engine.delete(collection, item_id):
            raise HTTPException(status_code=404, detail="Entry not found")
        return {"deleted": True}

    @app.post("/api/diagnostics/bot-api")
    async def bot_api_diagnostics(x_web_pin: str | None = Header(default=None)) -> dict[str, Any]:
        authorize(x_web_pin)
        try:
            return await engine.diagnose_control_bot()
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket) -> None:
        pin = websocket.query_params.get("pin")
        if settings.web_pin and not hmac.compare_digest(pin or "", settings.web_pin):
            await websocket.close(code=1008)
            return
        await websocket.accept()
        queue = await engine.subscribe()
        try:
            while True:
                event = await queue.get()
                await websocket.send_json(event)
        except WebSocketDisconnect:
            pass
        finally:
            engine.unsubscribe(queue)

    return app
