"""AUSHADHI — health center models.

Mirrors the `health_centers` collection in docs/DATABASE_SCHEMA.md.
All timestamps are ISO 8601 UTC strings (Firestore serialization).
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

CenterType = Literal["SC", "PHC", "CHC", "DH"]
StockStatus = Literal["CRITICAL", "LOW", "MODERATE", "GOOD"]
ReportingStatus = Literal["ON_TIME", "DELAYED", "MISSING"]


class GeoLocation(BaseModel):
    """Latitude/longitude pair used for Haversine routing."""

    model_config = ConfigDict(extra="ignore")

    lat: float = Field(..., ge=-90.0, le=90.0)
    lng: float = Field(..., ge=-180.0, le=180.0)


class HealthCenterStatus(BaseModel):
    """Rolling status maintained by the Sentinel and DQMS agents."""

    model_config = ConfigDict(extra="ignore")

    last_checked: str
    overall_stock_status: StockStatus
    critical_items_count: int = 0
    low_items_count: int = 0
    data_quality_score: float = Field(1.0, ge=0.0, le=1.0)
    last_report_date: str
    reporting_status: ReportingStatus

    def to_firestore_dict(self) -> dict:
        return self.model_dump()


class HealthCenter(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    name: str
    type: CenterType
    district: str
    subdistrict: str
    address: str
    location: GeoLocation
    catchment_population: int = Field(..., ge=0)
    medical_officer: str
    contact_phone: str
    contact_email: str

    status: HealthCenterStatus

    nearest_warehouse_id: str
    nearest_warehouse_distance_km: float = Field(..., ge=0.0)

    created_at: str
    updated_at: str

    def to_firestore_dict(self, exclude_none: bool = True) -> dict:
        """Nested dict ready for a Firestore document write."""
        return self.model_dump(exclude_none=exclude_none)
