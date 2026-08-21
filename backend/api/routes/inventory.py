"""AUSHADHI — inventory endpoints."""

from typing import List, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, Query

from api.deps import firestore, paginate, pagination
from api.schemas import PaginatedResponse
from models.inventory import InventoryItem
from services.firestore_service import FirestoreService

router = APIRouter(tags=["inventory"])

CONSUMPTION_HISTORY_DAYS = 14


@router.get("/inventory", response_model=PaginatedResponse[InventoryItem])
async def list_inventory(
    center_id: Optional[str] = Query(None),
    urgency: Optional[str] = Query(None, description="CRITICAL | LOW | MONITOR | OK"),
    medicine_id: Optional[str] = Query(None),
    page: Tuple[int, int] = Depends(pagination),
    svc: FirestoreService = Depends(firestore),
) -> PaginatedResponse[InventoryItem]:
    limit, offset = page

    # Pick the narrowest indexed query available, then filter what's left in
    # process — the flat inventory collection is one document per center per
    # medicine, so this stays small.
    if center_id:
        items: List[InventoryItem] = await svc.get_inventory_for_center(center_id)
        if urgency:
            items = [i for i in items if i.urgency == urgency.upper()]
    elif urgency:
        items = await svc.get_inventory_by_urgency(urgency.upper())
    else:
        items = [
            InventoryItem(**snap.to_dict())
            async for snap in svc.db.collection("inventory").stream()
        ]

    if medicine_id:
        items = [i for i in items if i.medicine_id == medicine_id]

    urgency_rank = {"CRITICAL": 0, "LOW": 1, "MONITOR": 2, "OK": 3}
    items.sort(key=lambda i: (urgency_rank.get(i.urgency, 9), i.stock_percentage))

    page_items, total = paginate(items, limit, offset)
    return PaginatedResponse.build(page_items, total, limit, offset)


@router.get("/inventory/{center_id}/{medicine_id}")
async def get_inventory_item(
    center_id: str, medicine_id: str, svc: FirestoreService = Depends(firestore)
) -> dict:
    """One inventory line plus its 14-day consumption history."""
    item = await svc.get_inventory_item(center_id, medicine_id)
    if item is None:
        raise HTTPException(
            status_code=404,
            detail=f"No inventory for medicine '{medicine_id}' at center '{center_id}'",
        )

    history = await svc.get_consumption_history(
        center_id, medicine_id, days=CONSUMPTION_HISTORY_DAYS
    )
    return {
        **item.to_firestore_dict(),
        "consumption_history": [
            record.to_firestore_dict()
            for record in sorted(history, key=lambda r: r.report_date)
        ],
    }
