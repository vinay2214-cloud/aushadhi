"""AUSHADHI — Agent 2: DQMS Validation.

Trigger: subscribes to aushadhi-sentinel-alerts.
Gemini:  none — deterministic validation rules.

ConsumptionValidator is the port of the DQMS rule set in docs/AGENTS_SPEC.md
Agent 2, applied to the inventory records the Sentinel Agent alerted on:

    Rule 1  negative stock                       -> error   (-0.30)
    Rule 2  consumption exceeds opening stock    -> error   (-0.40)
    Rule 3  no update for 48h+                   -> warning (-0.20)
    Rule 4  consumption > 5x the 7-day average   -> warning, sets anomaly_flag
    Rule 5  duplicate center+medicine+date       -> warning, keep the better record
    Rule 6  required field missing               -> error   (-0.15 each)

Rule 4 is deliberately not a penalty: a consumption spike is the outbreak
signal the Forecast Agent exists to read, so it is flagged and forwarded, not
scored down. Records that fail a rule are rejected; the rest go on to
aushadhi-validated-data.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from google.cloud.firestore_v1.base_query import FieldFilter

from utils.logger import get_logger

from agents.base_agent import BaseAgent

log = get_logger(__name__)

TOPIC_VALIDATED_DATA = "validated-data"

REQUIRED_FIELDS = (
    "center_id",
    "medicine_id",
    "current_stock",
    "daily_consumption",
    "report_date",
)
STALE_DATA_HOURS = 48
ANOMALY_RATIO_THRESHOLD = 5.0
SUSPICIOUS_LOW_RATIO = 0.1


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_timestamp(value: Any) -> Optional[datetime]:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    return None


@dataclass
class ValidationResult:
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    quality_score: float
    processed_record: Dict[str, Any]


@dataclass
class BatchResult:
    center_id: str
    total_records: int
    valid_records: int
    rejected_records: int
    center_quality_score: float
    anomalies_detected: List[Dict[str, Any]] = field(default_factory=list)
    validated: List[Dict[str, Any]] = field(default_factory=list)
    rejected: List[Dict[str, Any]] = field(default_factory=list)


class ConsumptionValidator:
    """Port of DQMS validation logic applied to health center consumption data."""

    def validate_consumption_record(self, record: dict) -> ValidationResult:
        errors: List[str] = []
        warnings: List[str] = []
        quality_score = 1.0
        now = datetime.now(timezone.utc)

        # Rule 1: Stock cannot be negative
        if record.get("current_stock", 0) < 0:
            errors.append("NEGATIVE_STOCK: current_stock cannot be negative")
            quality_score -= 0.3

        # Rule 2: Daily consumption cannot exceed opening stock
        if record.get("daily_consumption", 0) > record.get("opening_stock", 0):
            errors.append("IMPOSSIBLE_CONSUMPTION: consumed more than opening stock")
            quality_score -= 0.4

        # Rule 3: Missing report flag (no data for 48+ hours)
        last_updated = _parse_timestamp(record.get("last_updated"))
        if last_updated is None:
            warnings.append("UNPARSEABLE_TIMESTAMP: last_updated could not be read")
            quality_score -= 0.1
        else:
            hours_since_update = (now - last_updated).total_seconds() / 3600
            if hours_since_update > STALE_DATA_HOURS:
                warnings.append(f"STALE_DATA: {hours_since_update:.0f}h since last update")
                quality_score -= 0.2

        # Rule 4: Statistical anomaly (consumption > 5x 7-day average)
        seven_day_avg = record.get("seven_day_avg_consumption", 0)
        if seven_day_avg > 0:
            ratio = record.get("daily_consumption", 0) / seven_day_avg
            if ratio > ANOMALY_RATIO_THRESHOLD:
                warnings.append(f"ANOMALY: consumption is {ratio:.1f}x the 7-day average")
                # A FEATURE, not a bug — a high ratio may be an outbreak, so the
                # record is flagged and forwarded rather than penalised.
                record["anomaly_flag"] = True
                record["anomaly_ratio"] = ratio
            elif ratio < SUSPICIOUS_LOW_RATIO and seven_day_avg > 10:
                warnings.append(
                    "SUSPICIOUS_LOW: consumption unexpectedly very low (under-reporting?)"
                )
                quality_score -= 0.1

        # Rule 5: Duplicate record check — see _flag_duplicates(), which needs
        # the whole batch plus Firestore and runs before this method.
        if record.get("duplicate_flag"):
            warnings.append(
                f"DUPLICATE_RECORD: {record.get('duplicate_count', 2)} records for "
                f"{record.get('center_id')}/{record.get('medicine_id')} on "
                f"{record.get('report_date')} — keeping the higher-quality record"
            )

        # Rule 6: Required fields present
        for required_field in REQUIRED_FIELDS:
            if required_field not in record or record[required_field] is None:
                errors.append(f"MISSING_FIELD: {required_field} is required")
                quality_score -= 0.15

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            quality_score=max(0.0, quality_score),
            processed_record=record,
        )

    def validate_center_batch(self, center_id: str, records: list) -> BatchResult:
        """Validate all records for a health center."""
        if not records:
            return BatchResult(center_id, 0, 0, 0, 1.0)

        results = [self.validate_consumption_record(r) for r in records]
        center_quality_score = sum(r.quality_score for r in results) / len(results)

        validated: List[Dict[str, Any]] = []
        rejected: List[Dict[str, Any]] = []
        for result in results:
            record = {
                **result.processed_record,
                "is_valid": result.is_valid,
                "validation_errors": result.errors,
                "validation_warnings": result.warnings,
                "quality_score": round(result.quality_score, 3),
            }
            (validated if result.is_valid else rejected).append(record)

        return BatchResult(
            center_id=center_id,
            total_records=len(records),
            valid_records=len(validated),
            rejected_records=len(rejected),
            center_quality_score=round(center_quality_score, 3),
            anomalies_detected=[
                {
                    "medicine_id": r.processed_record.get("medicine_id"),
                    "medicine_name": r.processed_record.get("medicine_name"),
                    "anomaly_ratio": r.processed_record.get("anomaly_ratio"),
                    "anomaly_flag": True,
                }
                for r in results
                if r.processed_record.get("anomaly_flag")
            ],
            validated=validated,
            rejected=rejected,
        )


class DQMSValidationAgent(BaseAgent):
    """Validates the Sentinel Agent's records before any Gemini call sees them."""

    name = "DQMS"
    action = "validate_center_batch"
    publishes_to = TOPIC_VALIDATED_DATA
    subscribes_to = "sentinel-alerts-sub"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.validator = ConsumptionValidator()

    async def process(
        self, center_id: Optional[str], payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        center_id = center_id or payload.get("center_id")
        report_date = str(payload.get("timestamp", _utc_now_iso()))[:10]

        records = [
            {**item, "center_id": center_id, "report_date": report_date}
            for item in list(payload.get("critical_items", []))
            + list(payload.get("low_items", []))
        ]

        await self._flag_duplicates(center_id, records, report_date)
        batch = self.validator.validate_center_batch(center_id, records)

        self.log.info(
            "dqms_batch_validated",
            cycle_id=payload.get("cycle_id"),
            center_id=center_id,
            total_records=batch.total_records,
            valid_records=batch.valid_records,
            rejected_records=batch.rejected_records,
            center_quality_score=batch.center_quality_score,
            anomalies=len(batch.anomalies_detected),
        )

        for record in batch.rejected:
            self.log.warning(
                "dqms_record_rejected",
                center_id=center_id,
                medicine_id=record.get("medicine_id"),
                errors=record.get("validation_errors"),
            )

        try:
            await self.firestore.update_health_center_status(
                center_id, {"data_quality_score": batch.center_quality_score}
            )
        except Exception as exc:
            self.log.warning(
                "dqms_quality_score_update_failed",
                center_id=center_id,
                error_type=type(exc).__name__,
                error=str(exc),
            )

        message = {
            "cycle_id": payload.get("cycle_id"),
            "center_id": center_id,
            "center_name": payload.get("center_name"),
            "center_type": payload.get("center_type"),
            "district": payload.get("district"),
            "subdistrict": payload.get("subdistrict"),
            "district_alert_count": payload.get("district_alert_count", 1),
            "report_date": report_date,
            "validation_summary": {
                "total_records": batch.total_records,
                "valid_records": batch.valid_records,
                "rejected_records": batch.rejected_records,
                "center_quality_score": batch.center_quality_score,
                "anomalies_detected": batch.anomalies_detected,
            },
            "validated_inventory": batch.validated,
            "rejected_records": batch.rejected,
            "action": "FORECAST_REQUIRED",
        }

        if not batch.validated:
            # Nothing survived validation: stop the pipeline here rather than
            # sending Gemini a prompt built from rejected data.
            self.log.warning(
                "dqms_no_valid_records", center_id=center_id, total=batch.total_records
            )
            return {**message["validation_summary"], "published": False, "center_id": center_id}

        message_id = await self.publish(message)
        self.log.info(
            "dqms_validated_data_published",
            center_id=center_id,
            message_id=message_id,
            valid_records=batch.valid_records,
        )

        return {
            "center_id": center_id,
            "published": True,
            "message_id": message_id,
            **message["validation_summary"],
        }

    async def _flag_duplicates(
        self, center_id: str, records: List[Dict[str, Any]], report_date: str
    ) -> None:
        """Rule 5: mark records that already have a filing for the same day.

        Equality-only queries need no composite index. A duplicate is a warning,
        never a rejection — the higher-quality record wins and the pipeline
        keeps moving.
        """
        for record in records:
            medicine_id = record.get("medicine_id")
            if not medicine_id:
                continue
            try:
                query = (
                    self.firestore.db.collection("consumption_records")
                    .where(filter=FieldFilter("center_id", "==", center_id))
                    .where(filter=FieldFilter("medicine_id", "==", medicine_id))
                    .where(filter=FieldFilter("report_date", "==", report_date))
                )
                existing = [snap.to_dict() async for snap in query.stream()]
            except Exception as exc:
                self.log.warning(
                    "dqms_duplicate_check_failed",
                    center_id=center_id,
                    medicine_id=medicine_id,
                    error_type=type(exc).__name__,
                    error=str(exc),
                )
                continue

            if len(existing) > 1:
                record["duplicate_flag"] = True
                record["duplicate_count"] = len(existing)
                best = max(existing, key=lambda r: r.get("quality_score", 0.0))
                record["duplicate_resolved_from"] = best.get("id")
