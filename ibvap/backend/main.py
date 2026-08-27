from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from backend.api.events import router as events_router
from backend.api import websocket
from backend.database import engine
from backend import models

from backend.websocket_manager import manager


app = FastAPI(
    title="IBVAP Backend",
    description="Intelligent Border Video Analytics Platform",
    version="1.0.0"
)


# Register API routers
app.include_router(events_router)
app.include_router(websocket.router)


@app.get("/")
def root():
    return {
        "status": "online",
        "service": "IBVAP Backend"
    }


@app.get("/health")
def health():
    try:
        with engine.connect():
            return {
                "status": "healthy",
                "database": "connected"
            }

    except Exception as e:
        return {
            "status": "error",
            "database": "disconnected",
            "message": str(e)
        }


@app.websocket("/ws/events")
async def websocket_events(websocket: WebSocket):

    await manager.connect(websocket)

    try:
        while True:
            # Keep the connection alive
            await websocket.receive_text()

    except WebSocketDisconnect:
        manager.disconnect(websocket)