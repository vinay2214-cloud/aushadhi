"""AUSHADHI — API v1 router.

Mounted by main.py at /api/v1. Every route below therefore answers at
/api/v1/<path> and requires X-API-Key (see api/middleware/auth.py), except
/api/v1/stream, which authenticates on ?api_key=.
"""

from fastapi import APIRouter

from api.routes import (
    agents,
    config,
    consumption,
    health_centers,
    internal,
    inventory,
    metrics,
    outbreaks,
    purchase_orders,
    stream,
    warehouses,
)

api_router = APIRouter()

api_router.include_router(metrics.router)
api_router.include_router(config.router)
api_router.include_router(health_centers.router)
api_router.include_router(inventory.router)
api_router.include_router(consumption.router)
api_router.include_router(outbreaks.router)
api_router.include_router(purchase_orders.router)
api_router.include_router(warehouses.router)
api_router.include_router(agents.router)
api_router.include_router(internal.router)
api_router.include_router(stream.router)

__all__ = ["api_router"]
