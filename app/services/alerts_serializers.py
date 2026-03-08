from app.models.alert import Alert
from app.schemas.alert import AlertDetailSchema, AlertListItemSchema
from app.schemas.common import DistanceSchema, LocationSchema


def to_alert_list_item_schema(alert: Alert) -> AlertListItemSchema:
    return AlertListItemSchema(
        alert_id=alert.alert_id,
        mode=alert.mode,
        detected_at=alert.detected_at,
        status=alert.status,
        severity=alert.severity,
        location=LocationSchema(
            latitude=alert.latitude,
            longitude=alert.longitude,
        )
        if alert.latitude is not None and alert.longitude is not None
        else None,
    )


def to_alert_detail_schema(alert: Alert) -> AlertDetailSchema:
    return AlertDetailSchema(
        alert_id=alert.alert_id,
        mode=alert.mode,
        live_session_id=alert.live_session_id,
        recording_id=alert.recording_id,
        device_id=alert.device_id,
        status=alert.status,
        risk_score=alert.risk_score,
        severity=alert.severity,
        priority=alert.priority,
        confidence=alert.confidence,
        distance=DistanceSchema(
            estimated_m=alert.distance_m,
            min_m=alert.distance_min_m,
            max_m=alert.distance_max_m,
            confidence=alert.distance_confidence,
        ),
        detected_at=alert.detected_at,
        created_at=alert.created_at,
        updated_at=alert.updated_at,
        location=LocationSchema(
            latitude=alert.latitude,
            longitude=alert.longitude,
        )
        if alert.latitude is not None and alert.longitude is not None
        else None,
    )