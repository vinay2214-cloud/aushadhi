"""AUSHADHI — system configuration and data quality reporting.

Both endpoints back the Settings screen:

    GET   /api/v1/config        — the stored system_config/main_config document
    PATCH /api/v1/config        — flip a runtime toggle (Gemma fallback)
    GET   /api/v1/data-quality  — per-center DQMS scores and reporting status
"""

from typing import Any, Dict, List

from fastapi import APIRouter, Body, Depends, HTTPException, Query

from api.deps import firestore, utc_now_iso
from config import settings
from services.firestore_service import FirestoreService
from utils.logger import get_logger

log = get_logger(__name__)

router = APIRouter(tags=["config"])

COLL_SYSTEM_CONFIG = "system_config"
CONFIG_DOC_ID = "main_config"

#: Keys PATCH /config may write. Everything else in the document is either
#: reference data or a deploy-time setting, and is rejected rather than
#: silently ignored.
PATCHABLE_KEYS = {"use_gemma_fallback"}


def _defaults_from_settings() -> Dict[str, Any]:
    """Fallback config when system_config/main_config has not been seeded."""
    return {
        "id": CONFIG_DOC_ID,
        "sentinel_poll_interval_minutes": settings.sentinel_poll_interval_minutes,
        "critical_threshold_percentage": settings.critical_threshold_percentage,
        "low_threshold_percentage": settings.low_threshold_percentage,
        "outbreak_detection_window_days": settings.outbreak_detection_window_days,
        "use_gemma_fallback": settings.use_gemma_fallback,
        "districts_monitored": [],
        "updated_at": None,
    }


@router.get("/config")
async def get_config(svc: FirestoreService = Depends(firestore)) -> Dict[str, Any]:
    """The stored system config, plus the live counts the dashboard displays.

    The Firestore document is returned as-is; the fields below it are derived
    at request time so the Settings screen reflects what is actually deployed
    rather than whatever was true when the document was last written.
    """
    snap = await svc.db.collection(COLL_SYSTEM_CONFIG).document(CONFIG_DOC_ID).get()

    if snap.exists:
        stored: Dict[str, Any] = snap.to_dict() or {}
        source = "firestore"
    else:
        stored = _defaults_from_settings()
        source = "settings_defaults"
        log.warning("system_config_missing", doc_id=CONFIG_DOC_ID, fallback=source)

    centers = await svc.get_all_health_centers()
    medicines = await svc.get_all_medicines()

    # districts_monitored is stored as a list of names; the UI wants a count,
    # so the list is preserved under `districts` and the count takes the name.
    districts = stored.get("districts_monitored")
    if not isinstance(districts, list):
        districts = sorted({c.district for c in centers})

    last_run = max(
        (c.status.last_checked for c in centers if c.status.last_checked), default=None
    )

    config = {
        **stored,
        "districts": districts,
        "districts_monitored": len(districts),
        "centers_monitored": len(centers),
        "medicines_tracked": len(medicines),
        "last_pipeline_run": last_run,
        # The live toggle, not the stored one: the process loads the stored
        # value at startup and PATCH /config updates both, so these agree —
        # but if they ever diverge, the Settings screen should show the model
        # that is actually answering.
        "active_model": settings.gemma_model if settings.use_gemma_fallback else settings.gemini_model,
        "gemma_fallback_enabled": settings.use_gemma_fallback,
        "gemini_model": settings.gemini_model,
        "gemma_model": settings.gemma_model,
        "gemini_auth": "vertex_ai",
        "vertex_location": settings.vertex_location,
        "environment": settings.environment,
        "version": settings.app_version,
        "config_source": source,
        "generated_at": utc_now_iso(),
    }

    log.info("config_read", source=source, centers=len(centers), medicines=len(medicines))
    return config


@router.patch("/config")
async def update_config(
    payload: Dict[str, Any] = Body(...),
    svc: FirestoreService = Depends(firestore),
) -> Dict[str, Any]:
    """Flip a runtime toggle. Currently only use_gemma_fallback.

    The value is written twice on purpose: to Firestore so it survives a
    restart and shows up in GET /config, and onto the live Settings object so
    GeminiService picks the other model up on its very next call instead of
    after a redeploy. That in-process half only reaches this replica — the
    deployment runs a single instance (AGENTS_IN_PROCESS=true means every
    replica would otherwise consume the same subscriptions), so that is the
    whole system; scale past one and the toggle needs a restart to spread.
    """
    unknown = sorted(set(payload) - PATCHABLE_KEYS)
    if unknown:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported config keys: {', '.join(unknown)}. "
                   f"Patchable keys: {', '.join(sorted(PATCHABLE_KEYS))}.",
        )

    updates = {key: bool(payload[key]) for key in payload if key in PATCHABLE_KEYS}
    if not updates:
        return {"updated": {}, "message": "No valid keys provided"}

    # set(merge=True), not update(): update() raises NotFound when
    # system_config/main_config has never been seeded.
    await svc.db.collection(COLL_SYSTEM_CONFIG).document(CONFIG_DOC_ID).set(
        {**updates, "updated_at": utc_now_iso()}, merge=True
    )

    for key, value in updates.items():
        setattr(settings, key, value)

    log.info("config_updated", **updates)
    return {
        "updated": updates,
        "message": "Config updated",
        "active_model": settings.gemma_model if settings.use_gemma_fallback else settings.gemini_model,
        "gemma_fallback_enabled": settings.use_gemma_fallback,
    }


@router.get("/data-quality")
async def get_data_quality(
    district: str | None = Query(None, description="Limit the report to one district"),
    svc: FirestoreService = Depends(firestore),
) -> Dict[str, Any]:
    """Per-center DQMS scores, as maintained by the DQMS agent on each cycle."""
    centers = await svc.get_all_health_centers(district=district)

    rows: List[Dict[str, Any]] = [
        {
            "center_id": center.id,
            "center_name": center.name,
            "district": center.district,
            "data_quality_score": center.status.data_quality_score,
            "reporting_status": center.status.reporting_status,
            "last_report_date": center.status.last_report_date,
        }
        for center in centers
    ]
    rows.sort(key=lambda r: r["data_quality_score"])

    scores = [r["data_quality_score"] for r in rows]
    on_time = sum(1 for r in rows if r["reporting_status"] == "ON_TIME")

    report = {
        "centers": rows,
        "district_average": round(sum(scores) / len(scores), 3) if scores else 0.0,
        "total_centers": len(rows),
        "centers_reporting_on_time": on_time,
        "district": district,
        "generated_at": utc_now_iso(),
    }

    log.info(
        "data_quality_report",
        district=district or "ALL",
        centers=len(rows),
        average=report["district_average"],
        on_time=on_time,
    )
    return report
