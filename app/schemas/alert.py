from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.common import DistanceSchema, LocationSchema


class AlertListItemSchema(BaseModel):
    alert_id: str
    mode: str
    detected_at: datetime
    status: str
    severity: str
    location: LocationSchema | None = None

    model_config = ConfigDict(from_attributes=True)


class AlertDetailSchema(BaseModel):
    alert_id: str
    mode: str
    live_session_id: int | None = None
    recording_id: int | None = None
    device_id: str | None = None
    status: str
    risk_score: int
    severity: str
    priority: str
    confidence: float | None = None
    distance: DistanceSchema
    detected_at: datetime
    created_at: datetime
    updated_at: datetime | None = None
    location: LocationSchema | None = None

    model_config = ConfigDict(from_attributes=True)
