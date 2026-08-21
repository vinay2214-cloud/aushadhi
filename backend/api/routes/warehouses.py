"""AUSHADHI — warehouse endpoint (stock availability for routing)."""

from typing import List

from fastapi import APIRouter, Depends

from api.deps import firestore
from models.warehouse import Warehouse
from services.firestore_service import FirestoreService

router = APIRouter(tags=["warehouses"])


@router.get("/warehouses", response_model=List[Warehouse])
async def list_warehouses(svc: FirestoreService = Depends(firestore)) -> List[Warehouse]:
    return await svc.get_all_warehouses()
