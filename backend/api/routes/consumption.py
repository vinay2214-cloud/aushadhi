"""AUSHADHI — daily consumption reporting endpoint.

The write path an ASHA worker's app (or the simulator) uses. Records are
validated with the same ConsumptionValidator the DQMS agent runs, so a record
filed through the API carries the same quality score the pipeline would give it.
"""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from agents.dqms_agent import ConsumptionValidator
from api.deps import firestore, utc_now_iso
from models.consumption_record import ConsumptionRecord
from services.firestore_service import FirestoreService
from utils.logger import get_logger

log = get_logger(__name__)

router = APIRouter(tags=["consumption"])

_validator = ConsumptionValidator()


class ConsumptionReport(BaseModel):
    model_config = ConfigDict(extra="ignore")

    center_id: str
    medicine_id: str
    opening_stock: int = Field(..., ge=0)
    received_stock: int = Field(0, ge=0)
    closing_stock: int = Field(..., ge=0)
    report_date: str = Field(..., description="YYYY-MM-DD")
    reported_by: str
    report_source: str = "MANUAL_API"


@router.post("/consumption", status_code=status.HTTP_202_ACCEPTED)
async def report_consumption(
    body: ConsumptionReport, svc: FirestoreService = Depends(firestore)
) -> dict:
    try:
        datetime.strptime(body.report_date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(
            status_code=400, detail="report_date must be a date in YYYY-MM-DD form"
        )

    daily_consumption = body.opening_stock + body.received_stock - body.closing_stock

    inventory = await svc.get_inventory_item(body.center_id, body.medicine_id)
    result = _validator.validate_consumption_record(
        {
            "center_id": body.center_id,
            "medicine_id": body.medicine_id,
            "report_date": body.report_date,
            "opening_stock": body.opening_stock,
            "current_stock": body.closing_stock,
            "daily_consumption": daily_consumption,
            "seven_day_avg_consumption": (
                inventory.seven_day_avg_consumption if inventory else 0
            ),
            "last_updated": utc_now_iso(),
        }
    )

    record = ConsumptionRecord(
        id=f"{body.center_id}_{body.medicine_id}_{body.report_date}",
        center_id=body.center_id,
        medicine_id=body.medicine_id,
        report_date=body.report_date,
        opening_stock=body.opening_stock,
        received_stock=body.received_stock,
        closing_stock=body.closing_stock,
        daily_consumption=daily_consumption,
        is_valid=result.is_valid,
        validation_errors=result.errors,
        validation_warnings=result.warnings,
        quality_score=round(result.quality_score, 3),
        reported_by=body.reported_by,
        report_source=body.report_source if body.report_source in
        ("MANUAL_API", "MOBILE_APP", "SIMULATED") else "MANUAL_API",
        created_at=utc_now_iso(),
    )
    await svc.db.collection("consumption_records").document(record.id).set(
        record.to_firestore_dict()
    )

    # Keep the inventory document in step so the next sentinel cycle sees it.
    if inventory is not None:
        seven_day_avg = inventory.seven_day_avg_consumption or 0
        ratio = round(daily_consumption / seven_day_avg, 2) if seven_day_avg else 0.0
        await svc.update_inventory_item(
            body.center_id,
            body.medicine_id,
            {
                "current_stock": body.closing_stock,
                "opening_stock_today": body.opening_stock,
                "daily_consumption_today": daily_consumption,
                "consumption_ratio": ratio,
                "stock_percentage": round(
                    body.closing_stock / inventory.maximum_capacity * 100, 1
                )
                if inventory.maximum_capacity
                else 0.0,
                "last_updated": utc_now_iso(),
                "last_reported_by": body.reported_by,
            },
        )

    log.info(
        "consumption_recorded",
        record_id=record.id,
        center_id=body.center_id,
        medicine_id=body.medicine_id,
        daily_consumption=daily_consumption,
        valid=result.is_valid,
        quality_score=record.quality_score,
    )
    return {
        "record_id": record.id,
        "validated": result.is_valid,
        "quality_score": record.quality_score,
        "daily_consumption": daily_consumption,
        "validation_errors": result.errors,
        "validation_warnings": result.warnings,
    }
