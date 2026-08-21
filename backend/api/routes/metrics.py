"""AUSHADHI — dashboard metrics endpoint."""

from collections import defaultdict
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query
from google.cloud.firestore_v1.base_query import FieldFilter

from api.deps import firestore, parse_period, utc_now_iso, window_start_iso
from api.schemas import DashboardMetrics, DistrictMetrics
from services.firestore_service import FirestoreService
from utils.logger import get_logger

log = get_logger(__name__)

router = APIRouter(tags=["metrics"])

ACTIVE_OUTBREAK_STATUSES = ("ACTIVE", "UNDER_RESPONSE")


@router.get("/metrics", response_model=DashboardMetrics)
async def dashboard_metrics(
    period: str = Query("24h", description="Rolling window for PO and pipeline figures"),
    district: Optional[str] = Query(None),
    svc: FirestoreService = Depends(firestore),
) -> DashboardMetrics:
    """Top-line numbers for the dashboard.

    `period` bounds the time-scoped figures (POs generated and their value);
    stock, outbreak, and pending-approval counts are current-state and are not
    windowed. `district` filters everything, and `by_district` is always
    computed from the unfiltered data so the dashboard can show both.
    """
    window = parse_period(period)
    since = window_start_iso(window)

    centers = await svc.get_all_health_centers()
    center_district = {c.id: c.district for c in centers}

    inventory: List[Dict[str, Any]] = [
        snap.to_dict()
        async for snap in svc.db.collection("inventory")
        .where(filter=FieldFilter("urgency", "==", "CRITICAL"))
        .stream()
    ]

    outbreaks = [snap.to_dict() async for snap in svc.db.collection("outbreak_alerts").stream()]
    active_outbreaks = [
        o for o in outbreaks if o.get("status") in ACTIVE_OUTBREAK_STATUSES
    ]

    orders = [snap.to_dict() async for snap in svc.db.collection("purchase_orders").stream()]
    pending_orders = [o for o in orders if o.get("status") == "PENDING_APPROVAL"]
    orders_in_window = [o for o in orders if (o.get("created_at") or "") >= since]

    # pipeline_last_run: the newest SENTINEL log, which is where a cycle begins.
    sentinel_logs = [
        snap.to_dict()
        async for snap in svc.db.collection("agent_logs")
        .where(filter=FieldFilter("agent_name", "==", "SENTINEL"))
        .stream()
    ]
    pipeline_last_run = max(
        (entry.get("created_at", "") for entry in sentinel_logs), default=""
    ) or None

    def in_district(value: Optional[str]) -> bool:
        return district is None or value == district

    scoped_centers = [c for c in centers if in_district(c.district)]
    scoped_inventory = [
        i for i in inventory if in_district(center_district.get(i.get("center_id")))
    ]
    scoped_active_outbreaks = [o for o in active_outbreaks if in_district(o.get("district"))]
    scoped_pending = [o for o in pending_orders if in_district(o.get("district"))]
    scoped_window_orders = [o for o in orders_in_window if in_district(o.get("district"))]

    quality_scores = [c.status.data_quality_score for c in scoped_centers]
    avg_quality = round(sum(quality_scores) / len(quality_scores), 3) if quality_scores else 0.0

    # Per-district breakdown, always from the unfiltered sets.
    per_district: Dict[str, DistrictMetrics] = defaultdict(DistrictMetrics)
    for center in centers:
        per_district[center.district].centers_monitored += 1
    for item in inventory:
        name = center_district.get(item.get("center_id"))
        if name:
            per_district[name].critical_stockouts += 1
    for outbreak in active_outbreaks:
        if outbreak.get("district"):
            per_district[outbreak["district"]].active_outbreak_alerts += 1
    for order in pending_orders:
        if order.get("district"):
            per_district[order["district"]].pending_purchase_orders += 1
    by_district_quality: Dict[str, List[float]] = defaultdict(list)
    for center in centers:
        by_district_quality[center.district].append(center.status.data_quality_score)
    for name, scores in by_district_quality.items():
        per_district[name].avg_data_quality_score = round(sum(scores) / len(scores), 3)

    metrics = DashboardMetrics(
        centers_monitored=len(scoped_centers),
        critical_stockouts=len(scoped_inventory),
        active_outbreak_alerts=len(scoped_active_outbreaks),
        pending_purchase_orders=len(scoped_pending),
        avg_data_quality_score=avg_quality,
        total_pos_generated_today=len(scoped_window_orders),
        total_pos_value_inr=round(
            sum(float(o.get("total_cost_inr") or 0) for o in scoped_window_orders), 2
        ),
        pipeline_last_run=pipeline_last_run,
        period=period,
        district=district,
        by_district=dict(per_district),
        generated_at=utc_now_iso(),
    )
    log.info(
        "metrics_computed",
        period=period,
        district=district or "ALL",
        centers=metrics.centers_monitored,
        critical=metrics.critical_stockouts,
        outbreaks=metrics.active_outbreak_alerts,
    )
    return metrics
