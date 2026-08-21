"""AUSHADHI — API request/response schemas.

Shapes here follow docs/API_CONTRACTS.md. Domain objects (HealthCenter,
InventoryItem, OutbreakAlert, PurchaseOrder) come from models/ and are
returned as-is; this module only adds the API-level envelopes and the small
request bodies the PATCH endpoints take.
"""

from typing import Any, Dict, Generic, List, Optional, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """List envelope used by every collection endpoint."""

    model_config = ConfigDict(extra="ignore")

    items: List[T]
    total: int
    limit: int
    offset: int
    has_more: bool

    @classmethod
    def build(cls, items: List[T], total: int, limit: int, offset: int) -> "PaginatedResponse[T]":
        return cls(
            items=items,
            total=total,
            limit=limit,
            offset=offset,
            has_more=offset + len(items) < total,
        )


class AcknowledgeOutbreakRequest(BaseModel):
    acknowledged_by: str = Field(..., min_length=1, max_length=200)


class ResolveOutbreakRequest(BaseModel):
    resolution_notes: str = Field(..., min_length=1, max_length=2000)


class ApprovePurchaseOrderRequest(BaseModel):
    approved_by: str = Field(..., min_length=1, max_length=200)


class AgentStatus(BaseModel):
    """One row of GET /api/v1/agents/status."""

    model_config = ConfigDict(extra="allow")  # per-agent extras (see routes/agents.py)

    name: str
    status: str
    last_run: Optional[str] = None
    runs_today: int = 0
    failures_today: int = 0
    avg_duration_ms: int = 0


class AgentStatusResponse(BaseModel):
    agents: List[AgentStatus]
    window_hours: float
    generated_at: str


class DistrictMetrics(BaseModel):
    centers_monitored: int = 0
    critical_stockouts: int = 0
    active_outbreak_alerts: int = 0
    pending_purchase_orders: int = 0
    avg_data_quality_score: float = 0.0


class DashboardMetrics(BaseModel):
    """GET /api/v1/metrics — the dashboard's top-line numbers."""

    centers_monitored: int
    critical_stockouts: int
    active_outbreak_alerts: int
    pending_purchase_orders: int
    avg_data_quality_score: float
    total_pos_generated_today: int
    total_pos_value_inr: float
    pipeline_last_run: Optional[str] = None
    period: str
    district: Optional[str] = None
    by_district: Dict[str, DistrictMetrics] = Field(default_factory=dict)
    generated_at: str


class TriggerResponse(BaseModel):
    """202 responses from the /internal endpoints."""

    model_config = ConfigDict(extra="allow")

    message: str
    started_at: str
