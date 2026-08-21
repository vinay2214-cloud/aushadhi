"""AUSHADHI — Agent 3: Forecast + Outbreak Detection. The heart of the system.

Trigger: subscribes to aushadhi-validated-data.
Gemini:  YES — both calls in the system live here.

Two very different shapes of work:

  * forecast_demand() runs per center, per medicine. Independent calls, issued
    concurrently under a small semaphore.

  * detect_outbreak() runs ONCE per district per cycle, over every center's
    consumption anomalies at the same time. Clustering across facilities is the
    entire signal — one center analysed alone can never produce it.

Because Pub/Sub delivers one message per center, this agent buffers each
district's centers (keyed by cycle_id + district) and only calls
detect_outbreak when the whole cycle has reported in — the Sentinel Agent
stamps every message with district_alert_count so the buffer knows how many to
expect. A stale buffer is flushed anyway rather than stranding a district
because one center's message failed.
"""

import asyncio
import json
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from models.outbreak import OutbreakAlert, OutbreakEvidence
from services.gemini_service import GeminiService, get_gemini_service
from utils.logger import get_logger

from agents.base_agent import BaseAgent

log = get_logger(__name__)

TOPIC_FORECAST_COMPLETE = "forecast-complete"

#: Concurrent Gemini forecast calls. Small on purpose — 503s under load are the
#: dominant failure mode and each call already retries with an 8s backoff.
MAX_CONCURRENT_FORECASTS = 4

#: A district buffer older than this is analysed with whatever arrived.
BUFFER_STALE_SECONDS = 120.0

CONSUMPTION_HISTORY_DAYS = 14


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class _DistrictBuffer:
    """Centers collected for one (cycle_id, district) pair, awaiting analysis."""

    cycle_id: str
    district: str
    expected: int
    first_seen: float
    report_date: str
    centers: List[Dict[str, Any]] = field(default_factory=list)
    messages: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def complete(self) -> bool:
        return len(self.centers) >= self.expected

    @property
    def age_seconds(self) -> float:
        return time.monotonic() - self.first_seen


class ForecastOutbreakAgent(BaseAgent):
    """Per-medicine demand forecasting plus district-wide outbreak detection."""

    name = "FORECAST"
    action = "forecast_and_detect"
    publishes_to = TOPIC_FORECAST_COMPLETE
    subscribes_to = "validated-data-sub"

    def __init__(self, *args: Any, gemini: Optional[GeminiService] = None, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.gemini = gemini or get_gemini_service()
        self._buffers: Dict[Tuple[str, str], _DistrictBuffer] = {}
        self._buffer_lock = asyncio.Lock()
        self._medicines: Dict[str, Any] = {}
        self._semaphore = asyncio.Semaphore(MAX_CONCURRENT_FORECASTS)

    # ─────────────────────────────── work ──────────────────────────────

    async def process(
        self, center_id: Optional[str], payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        center_id = center_id or payload.get("center_id")
        district = payload.get("district") or "UNKNOWN"
        cycle_id = payload.get("cycle_id") or "adhoc"
        report_date = payload.get("report_date") or _utc_now_iso()[:10]
        inventory = payload.get("validated_inventory", [])

        center = await self.firestore.get_health_center(center_id)
        if center is None:
            raise ValueError(f"health center {center_id} not found in Firestore")

        await self._load_medicines()

        # ---- Gemini call 1..N: demand forecast per CRITICAL medicine ----
        # AGENTS_SPEC.md Agent 3 forecasts "per critical medicine": LOW items
        # still feed the outbreak prompt below, they just don't each cost a
        # Gemini call.
        critical = [item for item in inventory if item.get("urgency") == "CRITICAL"]
        forecasts = await self._forecast_center(center, critical, report_date)

        # ---- Buffer this center for the district-wide outbreak analysis ----
        outbreak_entry = self._build_outbreak_entry(center, inventory)
        forecast_message = {
            "cycle_id": cycle_id,
            "center_id": center_id,
            "center_name": center.name,
            "center_type": center.type,
            "district": district,
            "subdistrict": center.subdistrict,
            "report_date": report_date,
            "data_quality_score": payload.get("validation_summary", {}).get(
                "center_quality_score"
            ),
            "forecasts": forecasts,
            "action": "PROCUREMENT_REQUIRED",
        }

        async with self._buffer_lock:
            key = (cycle_id, district)
            buffer = self._buffers.get(key)
            if buffer is None:
                buffer = _DistrictBuffer(
                    cycle_id=cycle_id,
                    district=district,
                    expected=max(1, int(payload.get("district_alert_count", 1))),
                    first_seen=time.monotonic(),
                    report_date=report_date,
                )
                self._buffers[key] = buffer
            buffer.centers.append(outbreak_entry)
            buffer.messages.append(forecast_message)

            ready = buffer.complete
            stale = [k for k, b in self._buffers.items() if k != key and b.age_seconds > BUFFER_STALE_SECONDS]
            if ready:
                self._buffers.pop(key, None)
            stale_buffers = [self._buffers.pop(k) for k in stale]

        self.log.info(
            "forecast_center_complete",
            cycle_id=cycle_id,
            center_id=center_id,
            forecasts=len(forecasts),
            district=district,
            district_batch_ready=ready,
        )

        for buffer in stale_buffers:
            self.log.warning(
                "forecast_buffer_stale_flush",
                cycle_id=buffer.cycle_id,
                district=buffer.district,
                have=len(buffer.centers),
                expected=buffer.expected,
            )
            await self._analyze_and_publish(buffer)

        outbreak_result: Dict[str, Any] = {"analyzed": False}
        if ready:
            outbreak_result = await self._analyze_and_publish(buffer)

        return {
            "center_id": center_id,
            "district": district,
            "forecasts_generated": len(forecasts),
            "critical_forecasts": sum(
                1
                for f in forecasts
                if f["forecast"].get("reorder_urgency") in ("CRITICAL", "HIGH")
            ),
            "district_batch_ready": ready,
            "outbreak": outbreak_result,
        }

    async def flush_pending(self) -> List[Dict[str, Any]]:
        """Analyse every buffered district now, complete or not.

        The orchestrator calls this when a cycle winds down so a district that
        lost a message still gets its outbreak analysis.
        """
        async with self._buffer_lock:
            pending = list(self._buffers.values())
            self._buffers.clear()

        results = []
        for buffer in pending:
            self.log.info(
                "forecast_buffer_forced_flush",
                cycle_id=buffer.cycle_id,
                district=buffer.district,
                have=len(buffer.centers),
                expected=buffer.expected,
            )
            results.append(await self._analyze_and_publish(buffer))
        return results

    # ────────────────────── GEMINI 1: demand forecast ───────────────────

    async def _forecast_center(
        self, center, inventory: List[Dict[str, Any]], report_date: str
    ) -> List[Dict[str, Any]]:
        center_dict = {
            "id": center.id,
            "name": center.name,
            "type": center.type,
            "district": center.district,
            "catchment_population": center.catchment_population,
        }

        tasks = [
            self._forecast_item(center_dict, item, report_date)
            for item in inventory
            if item.get("medicine_id")
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        forecasts: List[Dict[str, Any]] = []
        for item, result in zip(inventory, results):
            if isinstance(result, BaseException):
                # One medicine failing must not sink the center's whole batch.
                self.log.error(
                    "forecast_item_failed",
                    center_id=center.id,
                    medicine_id=item.get("medicine_id"),
                    error_type=type(result).__name__,
                    error=str(result),
                )
                continue
            forecasts.append(result)
        return forecasts

    async def _forecast_item(
        self, center_dict: Dict[str, Any], item: Dict[str, Any], report_date: str
    ) -> Dict[str, Any]:
        medicine_id = item["medicine_id"]
        catalog = self._medicines.get(medicine_id)

        medicine_dict = {
            "id": medicine_id,
            "name": item.get("medicine_name") or (catalog.name if catalog else medicine_id),
            "category": catalog.category if catalog else "OTHER",
            "current_stock": item.get("current_stock", 0),
            "minimum_threshold": item.get("minimum_threshold", 0),
            "maximum_capacity": item.get("maximum_capacity", 0),
        }

        history = await self._consumption_history(
            center_dict["id"], medicine_id, item, report_date
        )

        async with self._semaphore:
            forecast = await self.gemini.forecast_demand(
                center=center_dict, medicine=medicine_dict, consumption_history=history
            )

        return {
            "medicine_id": medicine_id,
            "medicine_name": medicine_dict["name"],
            "category": medicine_dict["category"],
            "unit": catalog.unit if catalog else "units",
            "unit_cost_inr": catalog.unit_cost_inr if catalog else 0.0,
            "current_stock": medicine_dict["current_stock"],
            "minimum_threshold": medicine_dict["minimum_threshold"],
            "maximum_capacity": medicine_dict["maximum_capacity"],
            "sentinel_urgency": item.get("urgency"),
            "anomaly_flag": bool(item.get("anomaly_flag")),
            "anomaly_ratio": item.get("anomaly_ratio"),
            "history_days": len(history),
            "forecast": forecast,
        }

    async def _consumption_history(
        self,
        center_id: str,
        medicine_id: str,
        item: Dict[str, Any],
        report_date: str,
    ) -> List[Dict[str, Any]]:
        """Chronological history for the prompt, with today's row appended.

        Firestore's consumption_records hold yesterday and earlier; today's
        consumption (and the DQMS anomaly flag on it) lives on the inventory
        document, so it is appended as the final row — that last row is what
        gemini_service reads the anomaly flag from.
        """
        history: List[Dict[str, Any]] = []
        try:
            records = await self.firestore.get_consumption_history(
                center_id, medicine_id, days=CONSUMPTION_HISTORY_DAYS
            )
            history = [
                {
                    "date": record.report_date,
                    "daily_consumption": record.daily_consumption,
                    "opening_stock": record.opening_stock,
                }
                for record in sorted(records, key=lambda r: r.report_date)
            ]
        except Exception as exc:
            self.log.warning(
                "forecast_history_unavailable",
                center_id=center_id,
                medicine_id=medicine_id,
                error_type=type(exc).__name__,
                error=str(exc),
            )

        history.append(
            {
                "date": report_date,
                "daily_consumption": item.get("daily_consumption", 0),
                "opening_stock": item.get("opening_stock", 0),
                "anomaly_flag": bool(item.get("anomaly_flag")),
                "anomaly_ratio": item.get("anomaly_ratio"),
            }
        )
        return history

    # ───────────────────── GEMINI 2: outbreak detection ─────────────────

    async def _analyze_and_publish(self, buffer: _DistrictBuffer) -> Dict[str, Any]:
        """One detect_outbreak call for the district, then fan out to procurement."""
        outbreak: Dict[str, Any] = {"analyzed": False}
        alert_id: Optional[str] = None

        try:
            result = await self.gemini.detect_outbreak(
                centers_data=buffer.centers,
                district=buffer.district,
                date=buffer.report_date,
            )
            outbreak = {
                "analyzed": True,
                "outbreak_detected": bool(result.get("outbreak_detected")),
                "risk_level": result.get("risk_level"),
                "disease_indicators": result.get("disease_indicators", []),
                "affected_center_ids": result.get("affected_centers", []),
                "geographic_cluster": result.get("geographic_cluster"),
                "confidence": result.get("confidence"),
                "outbreak_summary": result.get("outbreak_summary"),
                "recommended_actions": result.get("recommended_actions", []),
                "recommended_surveillance_actions": result.get(
                    "recommended_surveillance_actions", []
                ),
                "key_evidence": result.get("key_evidence", []),
            }

            if result.get("outbreak_detected"):
                alert_id = await self._write_outbreak_alert(buffer.district, result)
                outbreak["outbreak_alert_id"] = alert_id
                self.log.info(
                    "outbreak_alert_created",
                    cycle_id=buffer.cycle_id,
                    district=buffer.district,
                    alert_id=alert_id,
                    risk_level=result.get("risk_level"),
                    confidence=result.get("confidence"),
                    disease_indicators=result.get("disease_indicators"),
                    affected_center_ids=result.get("affected_centers"),
                )
            else:
                self.log.info(
                    "outbreak_not_detected",
                    cycle_id=buffer.cycle_id,
                    district=buffer.district,
                    risk_level=result.get("risk_level"),
                    confidence=result.get("confidence"),
                )
        except Exception as exc:
            # Outbreak detection is the twist, but it must never block
            # restocking: procurement still gets its messages without it.
            self.log.error(
                "outbreak_detection_failed",
                cycle_id=buffer.cycle_id,
                district=buffer.district,
                error_type=type(exc).__name__,
                error=str(exc),
            )
            outbreak = {"analyzed": False, "error": f"{type(exc).__name__}: {exc}"}

        affected = set(outbreak.get("affected_center_ids") or [])
        published = []
        for message in buffer.messages:
            message["outbreak"] = {
                **outbreak,
                "center_affected": message["center_id"] in affected,
                "outbreak_alert_id": alert_id,
            }
            message_id = await self.publish(message)
            published.append(message_id)
            self.log.info(
                "forecast_complete_published",
                cycle_id=buffer.cycle_id,
                center_id=message["center_id"],
                forecasts=len(message["forecasts"]),
                outbreak_linked=bool(alert_id) and message["center_id"] in affected,
                message_id=message_id,
            )

        outbreak["published_messages"] = len(published)
        outbreak["centers_analyzed"] = len(buffer.centers)
        return outbreak

    async def _write_outbreak_alert(self, district: str, result: Dict[str, Any]) -> str:
        now = _utc_now_iso()
        evidence: List[OutbreakEvidence] = []
        for raw in result.get("key_evidence", []):
            try:
                evidence.append(OutbreakEvidence(**raw))
            except Exception as exc:
                self.log.warning(
                    "outbreak_evidence_skipped", error=str(exc), raw=str(raw)[:200]
                )

        alert = OutbreakAlert(
            id=f"outbreak_{uuid.uuid4().hex[:12]}",
            outbreak_detected=True,
            risk_level=result.get("risk_level", "MEDIUM"),
            disease_indicators=result.get("disease_indicators", []),
            affected_center_ids=result.get("affected_centers", []),
            geographic_cluster=result.get("geographic_cluster", ""),
            key_evidence=evidence,
            confidence=float(result.get("confidence", 0.0)),
            outbreak_summary=result.get("outbreak_summary", ""),
            differential_diagnosis=result.get("differential_diagnosis", ""),
            recommended_actions=result.get("recommended_actions", []),
            recommended_surveillance_actions=result.get(
                "recommended_surveillance_actions", []
            ),
            gemini_full_response=json.dumps(result),
            status="ACTIVE",
            district=district,
            created_at=now,
            updated_at=now,
        )
        return await self.firestore.create_outbreak_alert(alert)

    # ───────────────────────────── helpers ─────────────────────────────

    def _build_outbreak_entry(self, center, inventory: List[Dict[str, Any]]) -> Dict[str, Any]:
        """One center's row in the district-wide outbreak prompt.

        `id` is what detect_outbreak() maps Gemini's answer back onto, so the
        alert's affected_center_ids are real Firestore ids.
        """
        medicines = [
            {
                "name": item.get("medicine_name"),
                "current_consumption": item.get("daily_consumption", 0),
                "baseline_consumption": item.get("seven_day_avg_consumption", 0),
                "consumption_ratio": float(item.get("consumption_ratio", 0) or 0),
                "anomaly_flag": bool(item.get("anomaly_flag")),
            }
            for item in inventory
        ]
        return {
            "id": center.id,
            "name": center.name,
            "type": center.type,
            "subdistrict": center.subdistrict,
            "has_anomaly": any(m["anomaly_flag"] for m in medicines),
            "medicines": medicines,
        }

    async def _load_medicines(self) -> None:
        if self._medicines:
            return
        try:
            catalog = await self.firestore.get_all_medicines()
            self._medicines = {medicine.id: medicine for medicine in catalog}
            self.log.info("forecast_medicine_catalog_loaded", count=len(self._medicines))
        except Exception as exc:
            self.log.warning(
                "forecast_medicine_catalog_failed",
                error_type=type(exc).__name__,
                error=str(exc),
            )
