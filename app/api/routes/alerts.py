from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_db
from app.schemas.alert import AlertDetailSchema, AlertListItemSchema
from app.services.alerts import get_alert_by_alert_id, get_alerts
from app.services.alerts_serializers import to_alert_detail_schema, to_alert_list_item_schema

router = APIRouter(prefix="/alerts", tags=["Alerts"])


@router.get("", response_model=list[AlertListItemSchema])
def get_alerts_endpoint(
    status_filter: str | None = Query(default=None, alias="status"),
    severity: str | None = Query(default=None),
    priority: str | None = Query(default=None),
    device_id: str | None = Query(default=None),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    alerts = get_alerts(
        db=db,
        status=status_filter,
        severity=severity,
        priority=priority,
        device_id=device_id,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
    )
    return [to_alert_list_item_schema(alert) for alert in alerts]


@router.get("/{alert_id}", response_model=AlertDetailSchema)
def get_alert_detail_endpoint(alert_id: str, db: Session = Depends(get_db)):
    alert = get_alert_by_alert_id(db, alert_id)
    if alert is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")

    return to_alert_detail_schema(alert)
