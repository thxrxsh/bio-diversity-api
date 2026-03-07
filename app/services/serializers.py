from app.models.live_chunk import LiveChunk
from app.models.live_session import LiveSession
from app.models.recording import Recording
from app.models.recording_chunk import RecordingChunk
from app.schemas.common import DistanceSchema, LocationSchema, ProbabilitySchema
from app.schemas.live_session import LiveChunkSchema, LiveSessionSummarySchema
from app.schemas.recording import RecordingChunkSchema, RecordingSummarySchema


def to_recording_summary_schema(recording: Recording) -> RecordingSummarySchema:
    return RecordingSummarySchema(
        id=recording.id,
        file_name=recording.file_name,
        saved_path=recording.saved_path,
        device_id=recording.device_id,
        status=recording.status,
        overall_label=recording.overall_label,
        overall_is_leopard=recording.overall_is_leopard,
        best_confidence=recording.best_confidence,
        best_chunk_id=recording.best_chunk_id,
        created_at=recording.created_at,
    )


def to_recording_chunk_schema(chunk: RecordingChunk) -> RecordingChunkSchema:
    return RecordingChunkSchema(
        id=chunk.id,
        recording_id=chunk.recording_id,
        chunk_index=chunk.chunk_index,
        start_sec=chunk.start_sec,
        end_sec=chunk.end_sec,
        label=chunk.label,
        is_leopard=chunk.is_leopard,
        confidence=chunk.confidence,
        probabilities=ProbabilitySchema(
            leopard=chunk.leopard_probability,
            non_leopard=chunk.non_leopard_probability,
        ),
        distance=DistanceSchema(
            estimated_m=chunk.distance_m,
            min_m=chunk.distance_min_m,
            max_m=chunk.distance_max_m,
            confidence=chunk.distance_confidence,
        ),
        created_at=chunk.created_at,
    )


def to_live_session_summary_schema(session: LiveSession) -> LiveSessionSummarySchema:
    return LiveSessionSummarySchema(
        id=session.id,
        device_id=session.device_id,
        status=session.status,
        processing_status=session.processing_status,
        overall_is_leopard=session.overall_is_leopard,
        best_confidence=session.best_confidence,
        last_location=LocationSchema(
            latitude=session.last_latitude,
            longitude=session.last_longitude,
        )
        if session.last_latitude is not None and session.last_longitude is not None
        else None,
        started_at=session.started_at,
        ended_at=session.ended_at,
        last_detected_at=session.last_detected_at,
        best_chunk_id=session.best_chunk_id,
    )


def to_live_chunk_schema(chunk: LiveChunk) -> LiveChunkSchema:
    return LiveChunkSchema(
        id=chunk.id,
        live_session_id=chunk.live_session_id,
        chunk_index=chunk.chunk_index,
        location=LocationSchema(
            latitude=chunk.latitude,
            longitude=chunk.longitude,
        ),
        label=chunk.label,
        is_leopard=chunk.is_leopard,
        confidence=chunk.confidence,
        probabilities=ProbabilitySchema(
            leopard=chunk.leopard_probability,
            non_leopard=chunk.non_leopard_probability,
        ),
        distance=DistanceSchema(
            estimated_m=chunk.distance_m,
            min_m=chunk.distance_min_m,
            max_m=chunk.distance_max_m,
            confidence=chunk.distance_confidence,
        ),
        created_at=chunk.created_at,
    )
