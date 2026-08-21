"""AUSHADHI — outbreak alert models.

Mirrors the `outbreak_alerts` collection in docs/DATABASE_SCHEMA.md.
Populated from the Gemini outbreak-detection response (see docs/AGENTS_SPEC.md).
All timestamps are ISO 8601 UTC strings.
"""

from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

RiskLevel = Literal["CRITICAL", "HIGH", "MEDIUM", "LOW", "NONE"]
OutbreakStatus = Literal["ACTIVE", "UNDER_RESPONSE", "RESOLVED", "FALSE_POSITIVE"]
EvidenceSignificance = Literal["HIGH", "MEDIUM", "LOW"]


class OutbreakEvidence(BaseModel):
    """One consumption-signature data point supporting the alert."""

    model_config = ConfigDict(extra="ignore")

    medicine: str
    normal_daily_consumption: float
    current_daily_consumption: float
    ratio: float
    significance: EvidenceSignificance

    def to_firestore_dict(self) -> dict:
        return self.model_dump()


class OutbreakAlert(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str

    # ---- From Gemini outbreak detection ----
    outbreak_detected: bool
    risk_level: RiskLevel
    disease_indicators: List[str] = Field(default_factory=list)
    affected_center_ids: List[str] = Field(default_factory=list)
    geographic_cluster: str

    key_evidence: List[OutbreakEvidence] = Field(default_factory=list)

    confidence: float = Field(..., ge=0.0, le=1.0)
    outbreak_summary: str
    differential_diagnosis: str
    recommended_actions: List[str] = Field(default_factory=list)
    recommended_surveillance_actions: List[str] = Field(default_factory=list)
    gemini_full_response: str

    # ---- Status tracking ----
    status: OutbreakStatus = "ACTIVE"
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[str] = None
    resolved_at: Optional[str] = None
    resolution_notes: Optional[str] = None

    # ---- Linked emergency procurement ----
    linked_po_ids: List[str] = Field(default_factory=list)

    district: str
    created_at: str
    updated_at: str

    def to_firestore_dict(self, exclude_none: bool = False) -> dict:
        """Firestore document body.

        Acknowledgement/resolution fields are written as explicit nulls by
        default so clearing them overwrites the stored value.
        """
        return self.model_dump(exclude_none=exclude_none)
