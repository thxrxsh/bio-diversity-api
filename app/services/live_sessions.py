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


def _chunk_confidence(chunk: LiveChunk) -> float:
    return float(chunk.confidence) if chunk.confidence is not None else 0.0


def _p_leopard(chunk: LiveChunk) -> float:
    return float(chunk.leopard_probability) if chunk.leopard_probability is not None else 0.0


def _p_non_leopard(chunk: LiveChunk) -> float:
    return float(chunk.non_leopard_probability) if chunk.non_leopard_probability is not None else 0.0


def _avg_conf(chunks: list[LiveChunk]) -> float | None:
    if not chunks:
        return None
    return sum(_chunk_confidence(chunk) for chunk in chunks) / len(chunks)


def _get_all_session_chunks(db: Session, live_session_id: int) -> list[LiveChunk]:
    return (
        db.query(LiveChunk)
        .filter(LiveChunk.live_session_id == live_session_id)
        .order_by(LiveChunk.chunk_index.asc())
        .all()
    )


def update_live_session_summary(db: Session, session: LiveSession, latest_chunk: LiveChunk) -> bool:
    if latest_chunk.latitude is not None:
        session.last_latitude = latest_chunk.latitude
    if latest_chunk.longitude is not None:
        session.last_longitude = latest_chunk.longitude

    chunks = _get_all_session_chunks(db, session.id)

    if not chunks:
        session.overall_is_leopard = False
        session.best_confidence = None
        session.best_chunk_id = None
        return False

    num_chunks = len(chunks)
    overall_is_leopard = False
    chosen_chunk: LiveChunk | None = None
    chosen_confidence: float | None = None

    # ---------- 1 CHUNK ----------
    if num_chunks == 1:
        only_chunk = chunks[0]
        overall_is_leopard = only_chunk.label == "leopard"
        chosen_chunk = only_chunk
        chosen_confidence = _chunk_confidence(only_chunk)

    # ---------- 2 CHUNKS ----------
    elif num_chunks == 2:
        c1, c2 = chunks[0], chunks[1]

        if c1.label == c2.label:
            overall_is_leopard = c1.label == "leopard"
            chosen_chunk = max([c1, c2], key=_chunk_confidence)
            chosen_confidence = _avg_conf([c1, c2])
        else:
            leopard_chunk = next((c for c in chunks if c.label == "leopard"), None)
            non_leopard_chunk = next((c for c in chunks if c.label == "non_leopard"), None)

            if leopard_chunk is not None and _p_leopard(leopard_chunk) > 0.7:
                overall_is_leopard = True
                chosen_chunk = leopard_chunk
                chosen_confidence = _chunk_confidence(leopard_chunk)
            else:
                overall_is_leopard = False
                chosen_chunk = non_leopard_chunk if non_leopard_chunk is not None else max(chunks, key=_chunk_confidence)
                chosen_confidence = _chunk_confidence(chosen_chunk)

    # ---------- 3+ CHUNKS ----------
    else:
        valid_leopard_chunks = [chunk for chunk in chunks if _p_leopard(chunk) > 0.6]
        has_strong_leopard = any(_p_leopard(chunk) > 0.7 for chunk in valid_leopard_chunks)

        if len(valid_leopard_chunks) >= 2 and has_strong_leopard:
            overall_is_leopard = True
            chosen_chunk = max(valid_leopard_chunks, key=_p_leopard)
            chosen_confidence = _avg_conf(valid_leopard_chunks)
        else:
            overall_is_leopard = False
            non_leopard_chunks = [chunk for chunk in chunks if chunk.label == "non_leopard"]
            chosen_chunk = max(non_leopard_chunks or chunks, key=_p_non_leopard)
            chosen_confidence = _avg_conf(non_leopard_chunks or chunks)

    previous_state = bool(session.overall_is_leopard)

    session.overall_is_leopard = overall_is_leopard
    session.best_confidence = chosen_confidence
    session.best_chunk_id = chosen_chunk.id if chosen_chunk is not None else None

    if chosen_chunk is not None:
        session.distance_m = chosen_chunk.distance_m
        session.distance_min_m = chosen_chunk.distance_min_m
        session.distance_max_m = chosen_chunk.distance_max_m
        session.distance_confidence = chosen_chunk.distance_confidence

    if overall_is_leopard and not previous_state:
        session.last_detected_at = latest_chunk.created_at or datetime.utcnow()

    return overall_is_leopard and not previous_state


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

        became_leopard_now = update_live_session_summary(db, session, chunk)

        if became_leopard_now:
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