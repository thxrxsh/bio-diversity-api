from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, get_predictor
from app.schemas.live_session import (
    LiveChunkSchema,
    LiveChunkUploadResponseSchema,
    LiveSessionCreateResponseSchema,
    LiveSessionSummarySchema,
)
from app.services.live_sessions import (
    accept_live_chunk,
    create_live_session,
    end_live_session,
    get_live_chunks,
    get_live_session_by_id,
)
from app.services.serializers import to_live_chunk_schema, to_live_session_summary_schema

router = APIRouter(prefix="/live-sessions", tags=["Live Sessions"])


@router.post("", response_model=LiveSessionCreateResponseSchema, status_code=status.HTTP_201_CREATED)
def create_live_session_endpoint(
    device_id: str | None = Form(default=None),
    db: Session = Depends(get_db),
):
    session = create_live_session(db=db, device_id=device_id)
    return LiveSessionCreateResponseSchema(id=session.id, status=session.status)


@router.post(
    "/{live_id}/chunks",
    response_model=LiveChunkUploadResponseSchema,
    status_code=status.HTTP_201_CREATED,
)
def upload_live_chunk_endpoint(
    live_id: int,
    file: UploadFile = File(...),
    latitude: float | None = Form(default=None),
    longitude: float | None = Form(default=None),
    chunk_index: int | None = Form(default=None),
    db: Session = Depends(get_db),
):
    predictor = get_predictor()

    try:
        audio_bytes = file.file.read()
        result = accept_live_chunk(
            db=db,
            live_session_id=live_id,
            audio_bytes=audio_bytes,
            predictor=predictor,
            latitude=latitude,
            longitude=longitude,
            chunk_index=chunk_index,
        )
        return LiveChunkUploadResponseSchema(
            session=to_live_session_summary_schema(result.session),
            chunk=to_live_chunk_schema(result.chunk),
        )
    except ValueError as exc:
        message = str(exc)
        if message == "Live session not found":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message) from exc
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload live chunk: {exc}",
        ) from exc


@router.get("/{live_id}", response_model=LiveSessionSummarySchema)
def get_live_session_endpoint(live_id: int, db: Session = Depends(get_db)):
    session = get_live_session_by_id(db, live_id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Live session not found")

    return to_live_session_summary_schema(session)


@router.get("/{live_id}/chunks", response_model=list[LiveChunkSchema])
def get_live_chunks_endpoint(live_id: int, db: Session = Depends(get_db)):
    session = get_live_session_by_id(db, live_id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Live session not found")

    chunks = get_live_chunks(db, live_id)
    return [to_live_chunk_schema(chunk) for chunk in chunks]


@router.post("/{live_id}/end", response_model=LiveSessionSummarySchema)
def end_live_session_endpoint(live_id: int, db: Session = Depends(get_db)):
    try:
        session = end_live_session(db, live_id)
        return to_live_session_summary_schema(session)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
