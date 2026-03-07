from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.dependencies import get_db
from app.schemas.history import HistoryItemSchema
from app.services.history import (
    fetch_live_sessions_history,
    fetch_recordings_history,
    fetch_unified_history,
)

router = APIRouter(prefix="/history", tags=["History"])


@router.get("", response_model=list[HistoryItemSchema])
def get_history_endpoint(
    source: str = Query(default="all", pattern="^(all|recording|live)$"),
    device_id: str | None = Query(default=None),
    is_leopard: bool | None = Query(default=None),
    status: str | None = Query(default=None),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    return fetch_unified_history(
        db=db,
        source=source,
        device_id=device_id,
        is_leopard=is_leopard,
        status=status,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
    )


@router.get("/recordings", response_model=list[HistoryItemSchema])
def get_recordings_history_endpoint(
    device_id: str | None = Query(default=None),
    is_leopard: bool | None = Query(default=None),
    status: str | None = Query(default=None),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    db: Session = Depends(get_db),
):
    return fetch_recordings_history(
        db=db,
        device_id=device_id,
        is_leopard=is_leopard,
        status=status,
        date_from=date_from,
        date_to=date_to,
    )


@router.get("/live-sessions", response_model=list[HistoryItemSchema])
def get_live_sessions_history_endpoint(
    device_id: str | None = Query(default=None),
    is_leopard: bool | None = Query(default=None),
    status: str | None = Query(default=None),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    db: Session = Depends(get_db),
):
    return fetch_live_sessions_history(
        db=db,
        device_id=device_id,
        is_leopard=is_leopard,
        status=status,
        date_from=date_from,
        date_to=date_to,
    )
