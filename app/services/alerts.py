from __future__ import annotations

import random
import string
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.alert import Alert
from app.models.live_chunk import LiveChunk
from app.models.live_session import LiveSession


def generate_alert_id(length: int = 6) -> str:
    alphabet = string.ascii_uppercase + string.digits
    return "".join(random.choices(alphabet, k=length))


def _generate_unique_alert_id(db: Session) -> str:
    while True:
        candidate = generate_alert_id()
        exists = db.query(Alert).filter(Alert.alert_id == candidate).first()
        if not exists:
            return candidate


def calculate_risk_score(
    leopard_confidence: float | None,
    distance_m: float | None,
    distance_confidence: float | None,
) -> int:
    confidence_score = (leopard_confidence or 0.0) * 60
    distance_confidence_score = (distance_confidence or 0.0) * 20

    if distance_m is None:
        proximity_score = 10
    elif distance_m <= 50:
        proximity_score = 20
    elif distance_m <= 100:
        proximity_score = 15
    elif distance_m <= 200:
        proximity_score = 10
    else:
        proximity_score = 5

    risk_score = confidence_score + distance_confidence_score + proximity_score
    return max(0, min(100, round(risk_score)))


def derive_severity(risk_score: int) -> str:
    if risk_score >= 85:
        return "critical"
    if risk_score >= 65:
        return "high"
    if risk_score >= 40:
        return "medium"
    return "low"


def derive_priority(risk_score: int) -> str:
    return derive_severity(risk_score)


def _pick_best_leopard_chunk(db: Session, live_session_id: int) -> LiveChunk | None:
    return (
        db.query(LiveChunk)
        .filter(LiveChunk.live_session_id == live_session_id)
        .filter(LiveChunk.is_leopard.is_(True))
        .order_by(LiveChunk.confidence.desc())
        .first()
    )


def create_or_update_alert_for_live_session(
    db: Session,
    live_session: LiveSession,
) -> Alert | None:
    if not live_session.overall_is_leopard:
        return None

    best_chunk = _pick_best_leopard_chunk(db, live_session.id)
    if best_chunk is None:
        return None

    risk_score = calculate_risk_score(
        leopard_confidence=best_chunk.confidence,
        distance_m=best_chunk.distance_m,
        distance_confidence=best_chunk.distance_confidence,
    )
    severity = derive_severity(risk_score)
    priority = derive_priority(risk_score)

    alert = db.query(Alert).filter(Alert.live_session_id == live_session.id).first()

    if alert is None:
        alert = Alert(
            alert_id=_generate_unique_alert_id(db),
            live_session_id=live_session.id,
            device_id=live_session.device_id,
            status="new",
            risk_score=risk_score,
            severity=severity,
            priority=priority,
            confidence=best_chunk.confidence,
            distance_m=best_chunk.distance_m,
            distance_min_m=best_chunk.distance_min_m,
            distance_max_m=best_chunk.distance_max_m,
            distance_confidence=best_chunk.distance_confidence,
            latitude=live_session.last_latitude,
            longitude=live_session.last_longitude,
            detected_at=live_session.last_detected_at or best_chunk.created_at,
        )
        db.add(alert)
        db.flush()
    else:
        alert.device_id = live_session.device_id
        alert.risk_score = risk_score
        alert.severity = severity
        alert.priority = priority
        alert.confidence = best_chunk.confidence
        alert.distance_m = best_chunk.distance_m
        alert.distance_min_m = best_chunk.distance_min_m
        alert.distance_max_m = best_chunk.distance_max_m
        alert.distance_confidence = best_chunk.distance_confidence
        alert.latitude = live_session.last_latitude
        alert.longitude = live_session.last_longitude
        alert.detected_at = live_session.last_detected_at or best_chunk.created_at
        alert.updated_at = datetime.utcnow()

    return alert


def get_alerts(
    db: Session,
    status: str | None = None,
    severity: str | None = None,
    priority: str | None = None,
    device_id: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[Alert]:
    query = db.query(Alert)

    if status is not None:
        query = query.filter(Alert.status == status)
    if severity is not None:
        query = query.filter(Alert.severity == severity)
    if priority is not None:
        query = query.filter(Alert.priority == priority)
    if device_id is not None:
        query = query.filter(Alert.device_id == device_id)
    if date_from is not None:
        query = query.filter(Alert.detected_at >= date_from)
    if date_to is not None:
        query = query.filter(Alert.detected_at <= date_to)

    return query.order_by(Alert.detected_at.desc()).offset(offset).limit(limit).all()


def get_alert_by_alert_id(db: Session, alert_id: str) -> Alert | None:
    return db.query(Alert).filter(Alert.alert_id == alert_id).first()
