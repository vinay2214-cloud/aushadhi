"""AUSHADHI — medicine catalog models.

Mirrors the `medicines` collection in docs/DATABASE_SCHEMA.md.
All timestamps are ISO 8601 UTC strings.
"""

from typing import List, Literal

from pydantic import BaseModel, ConfigDict, Field

MedicineCategory = Literal[
    "ANTIBIOTIC",
    "ANALGESIC",
    "ORS_ELECTROLYTE",
    "ANTIMALARIA",
    "IV_FLUID",
    "VITAMIN",
    "ANTIPARASITIC",
    "VACCINE",
    "OTHER",
]
OutbreakIndicatorSignificance = Literal["PRIMARY", "SECONDARY"]


class OutbreakIndicator(BaseModel):
    """Which disease a medicine's consumption spike can signal."""

    model_config = ConfigDict(extra="ignore")

    disease: str
    significance: OutbreakIndicatorSignificance
    baseline_ratio_threshold: float = Field(..., ge=0.0)

    def to_firestore_dict(self) -> dict:
        return self.model_dump()


class Medicine(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    name: str
    generic_name: str
    category: MedicineCategory
    unit: str
    essential: bool

    outbreak_indicators: List[OutbreakIndicator] = Field(default_factory=list)

    default_minimum_threshold_units: int = Field(..., ge=0)
    default_maximum_capacity_units: int = Field(..., ge=0)

    unit_cost_inr: float = Field(..., ge=0.0)
    created_at: str

    def to_firestore_dict(self, exclude_none: bool = True) -> dict:
        """Firestore document body.

        Catalog documents are write-once reference data with no nullable
        lifecycle fields, so unset values are dropped.
        """
        return self.model_dump(exclude_none=exclude_none)
