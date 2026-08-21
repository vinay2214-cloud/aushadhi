"""AUSHADHI — inventory models.

Mirrors `health_centers/{id}/inventory/{medicine_id}` in docs/DATABASE_SCHEMA.md.
All timestamps are ISO 8601 UTC strings.
"""

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

Urgency = Literal["CRITICAL", "LOW", "MONITOR", "OK"]


class InventoryItem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    center_id: str
    medicine_id: str
    medicine_name: str

    # ---- Stock levels ----
    current_stock: int = Field(..., ge=0)
    minimum_threshold: int = Field(..., ge=0)
    maximum_capacity: int = Field(..., ge=0)
    stock_percentage: float = Field(..., ge=0.0)

    # ---- Derived fields (Sentinel Agent) ----
    urgency: Urgency
    days_until_stockout: Optional[int] = None

    # ---- Consumption tracking ----
    opening_stock_today: int = 0
    daily_consumption_today: int = 0
    seven_day_avg_consumption: float = 0.0
    thirty_day_avg_consumption: float = 0.0
    consumption_ratio: float = 0.0
    anomaly_flag: bool = False
    anomaly_ratio: Optional[float] = None

    # ---- Pending orders ----
    pending_order_quantity: int = 0
    expected_stock_date: Optional[str] = None

    # ---- Metadata ----
    last_updated: str
    last_reported_by: str
    updated_at: str

    def to_firestore_dict(self, exclude_none: bool = False) -> dict:
        """Firestore document body.

        Nullable fields (`days_until_stockout`, `anomaly_ratio`,
        `expected_stock_date`) are written as explicit nulls by default so a
        cleared value overwrites a previous one instead of being left stale.
        """
        return self.model_dump(exclude_none=exclude_none)
