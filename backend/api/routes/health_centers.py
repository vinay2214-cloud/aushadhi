"""AUSHADHI — health center endpoints."""

from typing import List, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, Query

from api.deps import firestore, paginate, pagination
from api.schemas import PaginatedResponse
from models.health_center import HealthCenter
from services.firestore_service import FirestoreService

router = APIRouter(tags=["health-centers"])


@router.get("/health-centers", response_model=PaginatedResponse[HealthCenter])
async def list_health_centers(
    district: Optional[str] = Query(None, description="e.g. East Godavari"),
    status: Optional[str] = Query(
        None, description="Filter on status.overall_stock_status: CRITICAL/LOW/MODERATE/GOOD"
    ),
    page: Tuple[int, int] = Depends(pagination),
    svc: FirestoreService = Depends(firestore),
) -> PaginatedResponse[HealthCenter]:
    limit, offset = page
    centers: List[HealthCenter] = await svc.get_all_health_centers(district=district)

    if status:
        # overall_stock_status lives inside the nested status map; filtering it
        # server-side would need a composite index for no real benefit at this
        # collection size.
        wanted = status.upper()
        centers = [c for c in centers if c.status.overall_stock_status == wanted]

    centers.sort(key=lambda c: (c.district, c.name))
    items, total = paginate(centers, limit, offset)
    return PaginatedResponse.build(items, total, limit, offset)


@router.get("/health-centers/{center_id}", response_model=HealthCenter)
async def get_health_center(
    center_id: str, svc: FirestoreService = Depends(firestore)
) -> HealthCenter:
    center = await svc.get_health_center(center_id)
    if center is None:
        raise HTTPException(status_code=404, detail=f"Health center '{center_id}' not found")
    return center
