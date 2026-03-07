from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, get_predictor
from app.schemas.recording import (
    RecordingChunkSchema,
    RecordingCreateResponseSchema,
    RecordingSummarySchema,
    RecordingStatusSchema,
)
from app.services.recordings import get_recording_by_id, get_recording_chunks, process_recording
from app.services.serializers import to_recording_chunk_schema, to_recording_summary_schema

router = APIRouter(prefix="/recordings", tags=["Recordings"])


@router.post("", response_model=RecordingCreateResponseSchema, status_code=status.HTTP_201_CREATED)
def create_recording_endpoint(
    file: UploadFile = File(...),
    device_id: str | None = Form(default=None),
    db: Session = Depends(get_db),
):
    predictor = get_predictor()

    try:
        result = process_recording(
            db=db,
            upload_file=file,
            predictor=predictor,
            device_id=device_id,
        )
        return RecordingCreateResponseSchema(id=result.recording.id, status=result.recording.status)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process recording: {exc}",
        ) from exc


@router.get("/{recording_id}", response_model=RecordingSummarySchema)
def get_recording_endpoint(recording_id: int, db: Session = Depends(get_db)):
    recording = get_recording_by_id(db, recording_id)
    if recording is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recording not found")

    return to_recording_summary_schema(recording)


@router.get("/{recording_id}/chunks", response_model=list[RecordingChunkSchema])
def get_recording_chunks_endpoint(recording_id: int, db: Session = Depends(get_db)):
    recording = get_recording_by_id(db, recording_id)
    if recording is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recording not found")

    chunks = get_recording_chunks(db, recording_id)
    return [to_recording_chunk_schema(chunk) for chunk in chunks]


@router.get(
    "/{recording_id}/status",
    response_model=RecordingStatusSchema,
)
def get_recording_status_endpoint(
    recording_id: int,
    db: Session = Depends(get_db),
):
    recording = get_recording_by_id(db, recording_id)

    if recording is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recording not found",
        )

    return recording