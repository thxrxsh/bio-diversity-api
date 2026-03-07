from fastapi import FastAPI

from app.api.routes.alerts import router as alerts_router
from app.api.routes.history import router as history_router
from app.api.routes.live_sessions import router as live_sessions_router
from app.api.routes.recordings import router as recordings_router
from app.db.database import Base, engine
from app.models.alert import Alert
from app.models.live_chunk import LiveChunk
from app.models.live_session import LiveSession
from app.models.recording import Recording
from app.models.recording_chunk import RecordingChunk


def create_app() -> FastAPI:
    Base.metadata.create_all(bind=engine)

    app = FastAPI(title="Biodiversity Detection API")
    app.include_router(recordings_router)
    app.include_router(live_sessions_router)
    app.include_router(history_router)
    app.include_router(alerts_router)

    @app.get("/")
    def root():
        return {"message": "Biodiversity Detection API is running"}

    return app


app = create_app()
