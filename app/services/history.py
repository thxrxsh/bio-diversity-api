from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.models.live_session import LiveSession
from app.models.recording import Recording
from app.schemas.common import LocationSchema
from app.schemas.history import HistoryItemSchema


def _within_date_range(
    value: datetime,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> bool:
    if date_from is not None and value < date_from:
        return False
    if date_to is not None and value > date_to:
        return False
    return True


def fetch_recordings_history(
    db: Session,
    device_id: str | None = None,
    is_leopard: bool | None = None,
    status: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> list[HistoryItemSchema]:
    query = db.query(Recording)

    if device_id is not None:
        query = query.filter(Recording.device_id == device_id)
    if is_leopard is not None:
        query = query.filter(Recording.overall_is_leopard == is_leopard)
    if status is not None:
        query = query.filter(Recording.status == status)

    recordings = query.order_by(Recording.created_at.desc()).all()

    items: list[HistoryItemSchema] = []
    for recording in recordings:
        if not _within_date_range(recording.created_at, date_from, date_to):
            continue

        items.append(
            HistoryItemSchema(
                source="recording",
                id=recording.id,
                device_id=recording.device_id,
                status=recording.status,
                label=recording.overall_label,
                is_leopard=recording.overall_is_leopard,
                confidence=recording.best_confidence,
                created_at=recording.created_at,
                location=None,
            )
        )

    return items


def fetch_live_sessions_history(
    db: Session,
    device_id: str | None = None,
    is_leopard: bool | None = None,
    status: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> list[HistoryItemSchema]:
    query = db.query(LiveSession)

    if device_id is not None:
        query = query.filter(LiveSession.device_id == device_id)
    if is_leopard is not None:
        query = query.filter(LiveSession.overall_is_leopard == is_leopard)
    if status is not None:
        query = query.filter(LiveSession.status == status)

    sessions = query.order_by(LiveSession.started_at.desc()).all()

    items: list[HistoryItemSchema] = []
    for session in sessions:
        created_at = session.started_at
        if not _within_date_range(created_at, date_from, date_to):
            continue

        location = None
        if session.last_latitude is not None and session.last_longitude is not None:
            location = LocationSchema(
                latitude=session.last_latitude,
                longitude=session.last_longitude,
            )

        items.append(
            HistoryItemSchema(
                source="live",
                id=session.id,
                device_id=session.device_id,
                status=session.status,
                label="leopard" if session.overall_is_leopard else "non_leopard",
                is_leopard=session.overall_is_leopard,
                confidence=session.best_confidence,
                created_at=created_at,
                location=location,
            )
        )

    return items


def fetch_unified_history(
    db: Session,
    source: str = "all",
    device_id: str | None = None,
    is_leopard: bool | None = None,
    status: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[HistoryItemSchema]:
    items: list[HistoryItemSchema] = []

    if source in ("all", "recording"):
        items.extend(
            fetch_recordings_history(
                db=db,
                device_id=device_id,
                is_leopard=is_leopard,
                status=status,
                date_from=date_from,
                date_to=date_to,
            )
        )

    if source in ("all", "live"):
        items.extend(
            fetch_live_sessions_history(
                db=db,
                device_id=device_id,
                is_leopard=is_leopard,
                status=status,
                date_from=date_from,
                date_to=date_to,
            )
        )

    items.sort(key=lambda item: item.created_at, reverse=True)
    return items[offset : offset + limit]
