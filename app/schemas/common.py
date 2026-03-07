from pydantic import BaseModel


class ProbabilitySchema(BaseModel):
    leopard: float | None = None
    non_leopard: float | None = None


class DistanceSchema(BaseModel):
    estimated_m: float | None = None
    min_m: float | None = None
    max_m: float | None = None
    confidence: float | None = None


class LocationSchema(BaseModel):
    latitude: float | None = None
    longitude: float | None = None
