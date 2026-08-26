from fastapi import FastAPI

from backend.api.events import router as events_router
from backend.database import engine
from backend import models


app = FastAPI(
    title="IBVAP Backend",
    description="Intelligent Border Video Analytics Platform",
    version="1.0.0"
)


# Register API routers
app.include_router(events_router)


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