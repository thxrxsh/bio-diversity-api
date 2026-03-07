from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.common import DistanceSchema, ProbabilitySchema, RecordingStatus


class RecordingCreateResponseSchema(BaseModel):
    id: int
    status: str

    model_config = ConfigDict(from_attributes=True)


class RecordingStatusSchema(BaseModel):
    id: int
    status: RecordingStatus

    model_config = ConfigDict(from_attributes=True)


class RecordingChunkSchema(BaseModel):
    id: int
    recording_id: int
    chunk_index: int
    start_sec: float
    end_sec: float

    label: str | None = None
    is_leopard: bool
    confidence: float | None = None

    probabilities: ProbabilitySchema
    distance: DistanceSchema
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RecordingSummarySchema(BaseModel):
    id: int
    file_name: str
    saved_path: str
    device_id: str | None = None
    status: str

    overall_label: str | None = None
    overall_is_leopard: bool
    best_confidence: float | None = None
    best_chunk_id: int | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
