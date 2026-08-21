"""AUSHADHI — shared route dependencies and query helpers.

FirestoreService covers the queries the agents need. The dashboard asks for a
few shapes it does not have (filter inventory by center, list agent logs in a
time window, count a collection), so those live here as thin helpers over the
same AsyncClient rather than being scattered through the route modules.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException, Query
from google.cloud.firestore_v1.base_query import FieldFilter

from services.firestore_service import FirestoreService, get_firestore_service
from services.pubsub_service import PubSubService, get_pubsub_service

DEFAULT_LIMIT = 100
MAX_LIMIT = 500


def firestore() -> FirestoreService:
    return get_firestore_service()


def pubsub() -> PubSubService:
    return get_pubsub_service()


def pagination(
    limit: int = Query(DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
    offset: int = Query(0, ge=0),
) -> Tuple[int, int]:
    return limit, offset


def paginate(items: List[Any], limit: int, offset: int) -> Tuple[List[Any], int]:
    """Slice an in-memory result set. Returns (page, total).

    Firestore cursors would be better at scale, but every collection here is
    hackathon-sized (tens to low hundreds of documents) and several endpoints
    filter in-process anyway, so slicing keeps the totals honest.
    """
    return items[offset : offset + limit], len(items)


def parse_period(period: str) -> timedelta:
    """"24h" / "7d" / "90m" -> timedelta. Raises 400 on anything else."""
    raw = (period or "").strip().lower()
    units = {"m": "minutes", "h": "hours", "d": "days"}
    if len(raw) >= 2 and raw[-1] in units and raw[:-1].isdigit():
        value = int(raw[:-1])
        if value > 0:
            return timedelta(**{units[raw[-1]]: value})
    raise HTTPException(
        status_code=400,
        detail=f"Invalid period '{period}'. Use a value like 60m, 24h, or 7d.",
    )


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def window_start_iso(period: timedelta) -> str:
    return (datetime.now(timezone.utc) - period).isoformat()


async def stream_collection(
    svc: FirestoreService,
    collection: str,
    filters: Optional[List[Tuple[str, str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """Stream a collection with optional equality/range filters, as raw dicts."""
    query = svc.db.collection(collection)
    for field, op, value in filters or []:
        query = query.where(filter=FieldFilter(field, op, value))
    return [snap.to_dict() async for snap in query.stream()]
