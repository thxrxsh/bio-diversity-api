from datetime import datetime

from pydantic import BaseModel

from app.schemas.common import LocationSchema


class HistoryItemSchema(BaseModel):
    source: str
    id: int
    device_id: str | None = None
    status: str
    label: str | None = None
    is_leopard: bool
    confidence: float | None = None
    created_at: datetime
    location: LocationSchema | None = None
