"""AUSHADHI — daily consumption record models.

Mirrors the `consumption_records` collection in docs/DATABASE_SCHEMA.md.
Written by the consumption API and validated by the DQMS agent.
All timestamps are ISO 8601 UTC strings; `report_date` is a date-only string.
"""

from typing import List, Literal

from pydantic import BaseModel, ConfigDict, Field

ReportSource = Literal["MANUAL_API", "MOBILE_APP", "SIMULATED"]


class ConsumptionRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    center_id: str
    medicine_id: str

    report_date: str  # "2026-08-20" — date only, not a timestamp

    opening_stock: int = Field(..., ge=0)
    received_stock: int = Field(0, ge=0)
    closing_stock: int = Field(..., ge=0)
    daily_consumption: int  # opening + received - closing (can be negative if data is bad)

    # ---- DQMS fields ----
    is_valid: bool = True
    validation_errors: List[str] = Field(default_factory=list)
    validation_warnings: List[str] = Field(default_factory=list)
    quality_score: float = Field(1.0, ge=0.0, le=1.0)

    reported_by: str
    report_source: ReportSource

    created_at: str

    def to_firestore_dict(self, exclude_none: bool = True) -> dict:
        """Firestore document body.

        Consumption records are immutable once filed — DQMS only appends
        validation results — so there is no 'clear this value' case and
        unset values are dropped.
        """
        return self.model_dump(exclude_none=exclude_none)
