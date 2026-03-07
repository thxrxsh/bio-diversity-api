from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol

from sqlalchemy.orm import Session

from app.models.live_chunk import LiveChunk
from app.models.live_session import LiveSession
from app.services.alerts import create_or_update_alert_for_live_session
from app.schemas.common import LiveSessionStatus, ProcessingStatus

import tempfile
from pathlib import Path

from app.utils.audio_convert import (
    normalize_audio_to_wav,
    AudioConversionError,
)

class PredictorProtocol(Protocol):
    def predict(self, audio_bytes: bytes) -> dict[str, Any]: ...


@dataclass
class LiveChunkProcessResult:
    session: LiveSession
    chunk: LiveChunk


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


def create_live_session(db: Session, device_id: str | None = None) -> LiveSession:
    session = LiveSession(
        device_id=device_id,
        status=LiveSessionStatus.active,
        processing_status=ProcessingStatus.idle,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def _get_next_chunk_index(db: Session, live_session_id: int) -> int:
    last_chunk = (
        db.query(LiveChunk)
        .filter(LiveChunk.live_session_id == live_session_id)
        .order_by(LiveChunk.chunk_index.desc())
        .first()
    )
    if last_chunk is None:
        return 0
    return last_chunk.chunk_index + 1


def update_live_session_summary(session: LiveSession, chunk: LiveChunk) -> None:
    if chunk.latitude is not None:
        session.last_latitude = chunk.latitude
    if chunk.longitude is not None:
        session.last_longitude = chunk.longitude

    chunk_confidence = chunk.confidence if chunk.confidence is not None else -1.0
    current_best = session.best_confidence if session.best_confidence is not None else -1.0

    if chunk_confidence > current_best:
        session.best_confidence = chunk.confidence
        session.best_chunk_id = chunk.id

        session.distance_m = chunk.distance_m
        session.distance_min_m = chunk.distance_min_m
        session.distance_max_m = chunk.distance_max_m
        session.distance_confidence = chunk.distance_confidence

    if chunk.is_leopard:
        session.overall_is_leopard = True
        session.last_detected_at = chunk.created_at or datetime.utcnow()



def _normalize_audio_bytes_to_wav_bytes(audio_bytes: bytes) -> bytes:
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir_path = Path(temp_dir)

        raw_path = temp_dir_path / "input_audio"
        wav_dir = temp_dir_path / "wav"

        raw_path.write_bytes(audio_bytes)

        wav_path = normalize_audio_to_wav(
            input_path=raw_path,
            output_dir=wav_dir,
            output_name="normalized.wav",
            sample_rate=16000,
            channels=1,
        )

        return Path(wav_path).read_bytes()

def accept_live_chunk(
    db: Session,
    live_session_id: int,
    audio_bytes: bytes,
    predictor: PredictorProtocol,
    latitude: float | None = None,
    longitude: float | None = None,
    chunk_index: int | None = None,
) -> LiveChunkProcessResult:
    session = db.query(LiveSession).filter(LiveSession.id == live_session_id).first()
    if session is None:
        raise ValueError("Live session not found")
    if session.status != LiveSessionStatus.active:
        raise ValueError("Live session is not active")

    if chunk_index is None:
        chunk_index = _get_next_chunk_index(db, live_session_id)

    session.processing_status = ProcessingStatus.processing
    db.flush()

    try:
        normalized_audio_bytes = _normalize_audio_bytes_to_wav_bytes(audio_bytes)
        prediction = predictor.predict(normalized_audio_bytes)
        fields = _extract_prediction_fields(prediction)

        chunk = LiveChunk(
            live_session_id=live_session_id,
            chunk_index=chunk_index,
            latitude=latitude,
            longitude=longitude,
            **fields,
        )

        db.add(chunk)
        db.flush()
        db.refresh(chunk)

        update_live_session_summary(session, chunk)

        if chunk.is_leopard:
            create_or_update_alert_for_live_session(db, session)

        session.processing_status = ProcessingStatus.completed

        db.commit()
        db.refresh(chunk)
        db.refresh(session)

        return LiveChunkProcessResult(session=session, chunk=chunk)

    except AudioConversionError:
        session.processing_status = ProcessingStatus.failed
        db.commit()
        db.refresh(session)
        raise

    except Exception:
        session.processing_status = ProcessingStatus.failed
        db.commit()
        db.refresh(session)
        raise


def end_live_session(db: Session, live_session_id: int) -> LiveSession:
    session = db.query(LiveSession).filter(LiveSession.id == live_session_id).first()
    if session is None:
        raise ValueError("Live session not found")

    session.status = LiveSessionStatus.ended
    session.ended_at = datetime.utcnow()
    db.commit()
    db.refresh(session)
    return session


def get_live_session_by_id(db: Session, live_session_id: int) -> LiveSession | None:
    return db.query(LiveSession).filter(LiveSession.id == live_session_id).first()


def get_live_chunks(db: Session, live_session_id: int) -> list[LiveChunk]:
    return (
        db.query(LiveChunk)
        .filter(LiveChunk.live_session_id == live_session_id)
        .order_by(LiveChunk.chunk_index.asc())
        .all()
    )
