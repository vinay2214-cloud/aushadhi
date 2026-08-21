"""AUSHADHI — purchase order endpoints."""

from typing import List, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, Query

from api.deps import firestore, paginate, pagination, utc_now_iso
from api.schemas import ApprovePurchaseOrderRequest, PaginatedResponse
from models.purchase_order import PurchaseOrder
from services.firestore_service import FirestoreService
from utils.logger import get_logger

log = get_logger(__name__)

router = APIRouter(tags=["purchase-orders"])

COLL = "purchase_orders"
VALID_STATUSES = {"PENDING_APPROVAL", "APPROVED", "DISPATCHED", "DELIVERED", "CANCELLED"}
VALID_PRIORITIES = {"CRITICAL", "HIGH", "MEDIUM", "LOW"}


@router.get("/purchase-orders", response_model=PaginatedResponse[PurchaseOrder])
async def list_purchase_orders(
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    center_id: Optional[str] = Query(None),
    page: Tuple[int, int] = Depends(pagination),
    svc: FirestoreService = Depends(firestore),
) -> PaginatedResponse[PurchaseOrder]:
    limit, offset = page

    if status and status.upper() not in VALID_STATUSES:
        raise HTTPException(
            status_code=400, detail=f"Invalid status. One of: {sorted(VALID_STATUSES)}"
        )
    if priority and priority.upper() not in VALID_PRIORITIES:
        raise HTTPException(
            status_code=400, detail=f"Invalid priority. One of: {sorted(VALID_PRIORITIES)}"
        )

    orders: List[PurchaseOrder] = []
    async for snap in svc.db.collection(COLL).stream():
        try:
            orders.append(PurchaseOrder(**snap.to_dict()))
        except Exception as exc:
            log.error("po_model_validation_failed", doc_id=snap.id, error=str(exc))

    if status:
        orders = [o for o in orders if o.status == status.upper()]
    if priority:
        orders = [o for o in orders if o.priority == priority.upper()]
    if center_id:
        orders = [o for o in orders if o.health_center_id == center_id]

    orders.sort(key=lambda o: o.created_at, reverse=True)
    items, total = paginate(orders, limit, offset)
    return PaginatedResponse.build(items, total, limit, offset)


@router.get("/purchase-orders/{po_id}", response_model=PurchaseOrder)
async def get_purchase_order(
    po_id: str, svc: FirestoreService = Depends(firestore)
) -> PurchaseOrder:
    snap = await svc.db.collection(COLL).document(po_id).get()
    if not snap.exists:
        raise HTTPException(status_code=404, detail=f"Purchase order '{po_id}' not found")
    return PurchaseOrder(**snap.to_dict())


@router.patch("/purchase-orders/{po_id}/approve")
async def approve_purchase_order(
    po_id: str,
    body: ApprovePurchaseOrderRequest,
    svc: FirestoreService = Depends(firestore),
) -> dict:
    """District officer approval: PENDING_APPROVAL -> APPROVED."""
    snap = await svc.db.collection(COLL).document(po_id).get()
    if not snap.exists:
        raise HTTPException(status_code=404, detail=f"Purchase order '{po_id}' not found")

    po = PurchaseOrder(**snap.to_dict())
    if po.status != "PENDING_APPROVAL":
        raise HTTPException(
            status_code=409,
            detail=f"PO {po.po_number} is {po.status}; only PENDING_APPROVAL can be approved",
        )

    approved_at = utc_now_iso()
    await svc.update_po_status(
        po_id, "APPROVED", approved_by=body.approved_by, approved_at=approved_at
    )
    log.info(
        "purchase_order_approved",
        po_id=po_id,
        po_number=po.po_number,
        approved_by=body.approved_by,
        total_cost_inr=po.total_cost_inr,
    )
    return {
        "id": po_id,
        "po_number": po.po_number,
        "status": "APPROVED",
        "approved_by": body.approved_by,
        "approved_at": approved_at,
    }
