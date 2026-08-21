"""AUSHADHI — outbreak alert endpoints."""

from typing import List, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, Query

from api.deps import firestore, paginate, pagination, utc_now_iso
from api.schemas import (
    AcknowledgeOutbreakRequest,
    PaginatedResponse,
    ResolveOutbreakRequest,
)
from models.outbreak import OutbreakAlert
from services.firestore_service import FirestoreService
from utils.logger import get_logger

log = get_logger(__name__)

router = APIRouter(tags=["outbreaks"])

COLL = "outbreak_alerts"
VALID_STATUSES = {"ACTIVE", "UNDER_RESPONSE", "RESOLVED", "FALSE_POSITIVE"}


async def _load_alert(svc: FirestoreService, alert_id: str) -> OutbreakAlert:
    snap = await svc.db.collection(COLL).document(alert_id).get()
    if not snap.exists:
        raise HTTPException(status_code=404, detail=f"Outbreak alert '{alert_id}' not found")
    return OutbreakAlert(**snap.to_dict())


@router.get("/outbreaks", response_model=PaginatedResponse[OutbreakAlert])
async def list_outbreaks(
    status: Optional[str] = Query(None, description="ACTIVE | UNDER_RESPONSE | RESOLVED | FALSE_POSITIVE"),
    district: Optional[str] = Query(None),
    page: Tuple[int, int] = Depends(pagination),
    svc: FirestoreService = Depends(firestore),
) -> PaginatedResponse[OutbreakAlert]:
    limit, offset = page

    alerts: List[OutbreakAlert] = []
    async for snap in svc.db.collection(COLL).stream():
        try:
            alerts.append(OutbreakAlert(**snap.to_dict()))
        except Exception as exc:
            log.error("outbreak_model_validation_failed", doc_id=snap.id, error=str(exc))

    if status:
        wanted = status.upper()
        if wanted not in VALID_STATUSES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status '{status}'. One of: {sorted(VALID_STATUSES)}",
            )
        alerts = [a for a in alerts if a.status == wanted]
    if district:
        alerts = [a for a in alerts if a.district == district]

    alerts.sort(key=lambda a: a.created_at, reverse=True)
    items, total = paginate(alerts, limit, offset)
    return PaginatedResponse.build(items, total, limit, offset)


@router.get("/outbreaks/{alert_id}", response_model=OutbreakAlert)
async def get_outbreak(
    alert_id: str, svc: FirestoreService = Depends(firestore)
) -> OutbreakAlert:
    return await _load_alert(svc, alert_id)


@router.patch("/outbreaks/{alert_id}/acknowledge")
async def acknowledge_outbreak(
    alert_id: str,
    body: AcknowledgeOutbreakRequest,
    svc: FirestoreService = Depends(firestore),
) -> dict:
    """District officer takes ownership: ACTIVE -> UNDER_RESPONSE."""
    alert = await _load_alert(svc, alert_id)
    if alert.status in ("RESOLVED", "FALSE_POSITIVE"):
        raise HTTPException(
            status_code=409,
            detail=f"Alert '{alert_id}' is already {alert.status} and cannot be acknowledged",
        )

    acknowledged_at = utc_now_iso()
    await svc.update_outbreak_status(
        alert_id,
        "UNDER_RESPONSE",
        acknowledged_by=body.acknowledged_by,
        acknowledged_at=acknowledged_at,
    )
    log.info(
        "outbreak_acknowledged",
        alert_id=alert_id,
        acknowledged_by=body.acknowledged_by,
        district=alert.district,
    )
    return {
        "id": alert_id,
        "status": "UNDER_RESPONSE",
        "acknowledged_by": body.acknowledged_by,
        "acknowledged_at": acknowledged_at,
    }


@router.patch("/outbreaks/{alert_id}/resolve")
async def resolve_outbreak(
    alert_id: str,
    body: ResolveOutbreakRequest,
    svc: FirestoreService = Depends(firestore),
) -> dict:
    alert = await _load_alert(svc, alert_id)
    if alert.status == "RESOLVED":
        raise HTTPException(status_code=409, detail=f"Alert '{alert_id}' is already RESOLVED")

    resolved_at = utc_now_iso()
    await svc.update_outbreak_status(
        alert_id,
        "RESOLVED",
        resolution_notes=body.resolution_notes,
        resolved_at=resolved_at,
    )
    log.info("outbreak_resolved", alert_id=alert_id, district=alert.district)
    return {
        "id": alert_id,
        "status": "RESOLVED",
        "resolved_at": resolved_at,
        "resolution_notes": body.resolution_notes,
    }
