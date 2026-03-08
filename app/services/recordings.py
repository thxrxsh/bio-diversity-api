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
from app.schemas.common import RecordingStatus
from app.services.alerts import create_or_update_alert_for_recording
from app.services.audio_windowing import split_audio_into_windows


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

    def conf(chunk: RecordingChunk) -> float:
        return float(chunk.confidence) if chunk.confidence is not None else 0.0

    def p_leopard(chunk: RecordingChunk) -> float:
        return float(chunk.leopard_probability) if chunk.leopard_probability is not None else 0.0

    def p_non_leopard(chunk: RecordingChunk) -> float:
        return float(chunk.non_leopard_probability) if chunk.non_leopard_probability is not None else 0.0

    def avg_conf(chunk_list: list[RecordingChunk]) -> float | None:
        if not chunk_list:
            return None
        return sum(conf(chunk) for chunk in chunk_list) / len(chunk_list)

    num_chunks = len(chunks)

    # ---------- 1 WINDOW ----------
    if num_chunks == 1:
        only_chunk = chunks[0]

        recording.overall_label = only_chunk.label
        recording.overall_is_leopard = only_chunk.label == "leopard"
        recording.best_confidence = conf(only_chunk)
        recording.best_chunk_id = only_chunk.id
        recording.status = RecordingStatus.completed
        return

    # ---------- 2 WINDOWS ----------
    if num_chunks == 2:
        c1, c2 = chunks[0], chunks[1]

        # Same prediction from both windows
        if c1.label == c2.label:
            agreed_label = c1.label
            agreed_confidence = avg_conf([c1, c2])

            best_chunk = max([c1, c2], key=conf)

            recording.overall_label = agreed_label
            recording.overall_is_leopard = agreed_label == "leopard"
            recording.best_confidence = agreed_confidence
            recording.best_chunk_id = best_chunk.id
            recording.status = RecordingStatus.completed
            return

        # Mixed prediction: one leopard, one non_leopard
        leopard_chunk = next((c for c in chunks if c.label == "leopard"), None)
        non_leopard_chunk = next((c for c in chunks if c.label == "non_leopard"), None)

        if leopard_chunk is not None and p_leopard(leopard_chunk) > 0.7:
            recording.overall_label = "leopard"
            recording.overall_is_leopard = True
            recording.best_confidence = conf(leopard_chunk)
            recording.best_chunk_id = leopard_chunk.id
        else:
            # fallback to non_leopard side
            chosen_chunk = non_leopard_chunk if non_leopard_chunk is not None else max(chunks, key=conf)
            recording.overall_label = "non_leopard"
            recording.overall_is_leopard = False
            recording.best_confidence = conf(chosen_chunk)
            recording.best_chunk_id = chosen_chunk.id

        recording.status = RecordingStatus.completed
        return

    # ---------- 3 OR MORE WINDOWS ----------
    valid_leopard_chunks = [chunk for chunk in chunks if p_leopard(chunk) > 0.6]
    has_strong_leopard = any(p_leopard(chunk) > 0.7 for chunk in valid_leopard_chunks)

    if len(valid_leopard_chunks) >= 2 and has_strong_leopard:
        best_leopard_chunk = max(valid_leopard_chunks, key=p_leopard)

        recording.overall_label = "leopard"
        recording.overall_is_leopard = True
        recording.best_confidence = avg_conf(valid_leopard_chunks)
        recording.best_chunk_id = best_leopard_chunk.id
        recording.status = RecordingStatus.completed
        return

    # Otherwise non_leopard
    non_leopard_chunks = [chunk for chunk in chunks if chunk.label == "non_leopard"]
    best_non_leopard_chunk = max(
        non_leopard_chunks or chunks,
        key=lambda chunk: p_non_leopard(chunk),
    )

    recording.overall_label = "non_leopard"
    recording.overall_is_leopard = False
    recording.best_confidence = avg_conf(non_leopard_chunks or chunks)
    recording.best_chunk_id = best_non_leopard_chunk.id
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

        if recording.overall_is_leopard:
            create_or_update_alert_for_recording(db, recording)

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