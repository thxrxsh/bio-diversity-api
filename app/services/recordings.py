from __future__ import annotations

import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.config import RECORDINGS_UPLOAD_DIR
from app.models.recording import Recording
from app.models.recording_chunk import RecordingChunk
from app.services.audio_windowing import split_audio_into_windows
from app.schemas.common import RecordingStatus


class PredictorProtocol(Protocol):
    def predict(self, audio_bytes: bytes) -> dict[str, Any]: ...


@dataclass
class RecordingProcessResult:
    recording: Recording
    chunks: list[RecordingChunk]


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _extract_prediction_fields(prediction: dict[str, Any]) -> dict[str, Any]:
    probabilities = prediction.get("probabilities") or {}
    distance = prediction.get("distance") or {}

    return {
        "label": prediction.get("label"),
        "is_leopard": bool(prediction.get("is_leopard", False)),
        "confidence": _safe_float(prediction.get("confidence")),
        "leopard_probability": _safe_float(probabilities.get("leopard")),
        "non_leopard_probability": _safe_float(probabilities.get("non_leopard")),
        "distance_m": _safe_float(distance.get("estimated_m")),
        "distance_min_m": _safe_float(distance.get("min_m")),
        "distance_max_m": _safe_float(distance.get("max_m")),
        "distance_confidence": _safe_float(distance.get("confidence")),
    }


def save_uploaded_recording_file(
    upload_file: UploadFile,
    upload_dir: Path = RECORDINGS_UPLOAD_DIR,
) -> tuple[str, str]:
    upload_dir.mkdir(parents=True, exist_ok=True)

    original_name = upload_file.filename or "recording.wav"
    ext = Path(original_name).suffix or ".wav"
    stored_file_name = f"{uuid.uuid4().hex}{ext}"
    saved_path = upload_dir / stored_file_name

    with saved_path.open("wb") as out_file:
        while True:
            chunk = upload_file.file.read(1024 * 1024)
            if not chunk:
                break
            out_file.write(chunk)

    return str(saved_path), stored_file_name


def create_recording(
    db: Session,
    file_name: str,
    saved_path: str,
    device_id: str | None = None,
) -> Recording:
    recording = Recording(
        file_name=file_name,
        saved_path=saved_path,
        device_id=device_id,
        status=RecordingStatus.uploaded,
    )
    db.add(recording)
    db.commit()
    db.refresh(recording)
    return recording


def compute_recording_summary(recording: Recording, chunks: list[RecordingChunk]) -> None:
    if not chunks:
        recording.status = RecordingStatus.failed
        recording.overall_label = None
        recording.overall_is_leopard = False
        recording.best_confidence = None
        recording.best_chunk_id = None
        return

    leopard_chunks = [chunk for chunk in chunks if chunk.is_leopard]
    summary_pool = leopard_chunks or chunks

    best_chunk = max(
        summary_pool,
        key=lambda chunk: chunk.confidence if chunk.confidence is not None else -1.0,
    )

    recording.overall_label = best_chunk.label
    recording.overall_is_leopard = bool(leopard_chunks)
    recording.best_confidence = best_chunk.confidence
    recording.best_chunk_id = best_chunk.id
    recording.status = RecordingStatus.completed


def process_recording(
    db: Session,
    upload_file: UploadFile,
    predictor: PredictorProtocol,
    device_id: str | None = None,
    upload_dir: Path = RECORDINGS_UPLOAD_DIR,
    window_sec: float = 3.0,
    target_sr: int = 22050,
) -> RecordingProcessResult:
    saved_path, _ = save_uploaded_recording_file(upload_file, upload_dir=upload_dir)

    recording = create_recording(
        db=db,
        file_name=upload_file.filename or Path(saved_path).name,
        saved_path=saved_path,
        device_id=device_id,
    )

    created_chunks: list[RecordingChunk] = []

    try:
        recording.status = RecordingStatus.processing
        db.commit()
        db.refresh(recording)

        windows = split_audio_into_windows(
            audio_path=saved_path,
            window_sec=window_sec,
            target_sr=target_sr,
            include_last_partial=False,
        )

        if not windows:
            recording.status = RecordingStatus.failed
            db.commit()
            db.refresh(recording)
            return RecordingProcessResult(recording=recording, chunks=[])

        for window in windows:
            prediction = predictor.predict(window.audio_bytes)
            fields = _extract_prediction_fields(prediction)

            chunk_row = RecordingChunk(
                recording_id=recording.id,
                chunk_index=window.chunk_index,
                start_sec=window.start_sec,
                end_sec=window.end_sec,
                **fields,
            )
            db.add(chunk_row)
            db.flush()
            created_chunks.append(chunk_row)

        db.commit()

        for chunk in created_chunks:
            db.refresh(chunk)

        db.refresh(recording)
        compute_recording_summary(recording, created_chunks)

        db.add(recording)
        db.commit()
        db.refresh(recording)

        return RecordingProcessResult(recording=recording, chunks=created_chunks)

    except Exception:
        recording.status = RecordingStatus.failed
        db.commit()
        db.refresh(recording)
        raise


def get_recording_by_id(db: Session, recording_id: int) -> Recording | None:
    return db.query(Recording).filter(Recording.id == recording_id).first()


def get_recording_chunks(db: Session, recording_id: int) -> list[RecordingChunk]:
    return (
        db.query(RecordingChunk)
        .filter(RecordingChunk.recording_id == recording_id)
        .order_by(RecordingChunk.chunk_index.asc())
        .all()
    )
