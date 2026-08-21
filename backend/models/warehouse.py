"""AUSHADHI — warehouse models.

Mirrors the `warehouses` collection in docs/DATABASE_SCHEMA.md.
All timestamps are ISO 8601 UTC strings.
"""

from typing import List

from pydantic import BaseModel, ConfigDict, Field


class WarehouseLocation(BaseModel):
    model_config = ConfigDict(extra="ignore")

    lat: float = Field(..., ge=-90.0, le=90.0)
    lng: float = Field(..., ge=-180.0, le=180.0)
    address: str

    def to_firestore_dict(self) -> dict:
        return self.model_dump()


class WarehouseContact(BaseModel):
    model_config = ConfigDict(extra="ignore")

    phone: str
    email: str

    def to_firestore_dict(self) -> dict:
        return self.model_dump()


class WarehouseStockItem(BaseModel):
    """Simplified warehouse stock line (hackathon-scale)."""

    model_config = ConfigDict(extra="ignore")

    medicine_id: str
    medicine_name: str
    available_quantity: int = Field(..., ge=0)

    def to_firestore_dict(self) -> dict:
        return self.model_dump()


class Warehouse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    name: str
    district: str
    location: WarehouseLocation
    contact: WarehouseContact

    available_medicines: List[WarehouseStockItem] = Field(default_factory=list)

    operating_hours: str
    created_at: str
    updated_at: str

    def to_firestore_dict(self, exclude_none: bool = True) -> dict:
        """Firestore document body.

        Warehouse stock is always a list (possibly empty); there is no
        'clear this field to null' lifecycle, so unset extras are dropped.
        """
        return self.model_dump(exclude_none=exclude_none)
