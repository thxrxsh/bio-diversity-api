from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.common import DistanceSchema, LocationSchema, ProbabilitySchema
from app.schemas.common import LiveSessionStatus, ProcessingStatus

class LiveSessionCreateResponseSchema(BaseModel):
    id: int
    status: str

    model_config = ConfigDict(from_attributes=True)


class LiveSessionStatusSchema(BaseModel):
    id: int
    device_id: str | None = None
    status: LiveSessionStatus
    processing_status: ProcessingStatus


class LiveChunkSchema(BaseModel):
    id: int
    live_session_id: int
    chunk_index: int
    location: LocationSchema

    label: str | None = None
    is_leopard: bool
    confidence: float | None = None

    probabilities: ProbabilitySchema
    distance: DistanceSchema
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LiveSessionStatusSchema(BaseModel):
    id: int
    device_id: str | None = None
    status: str
    processing_status: str

    overall_is_leopard: bool
    best_confidence: float | None = None
    last_location: LocationSchema

    started_at: datetime
    ended_at: datetime | None = None
    last_detected_at: datetime | None = None
    best_chunk_id: int | None = None

    model_config = ConfigDict(from_attributes=True)


class LiveChunkUploadResponseSchema(BaseModel):
    session: LiveSessionStatusSchema
    chunk: LiveChunkSchema
