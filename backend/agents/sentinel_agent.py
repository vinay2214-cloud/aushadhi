"""AUSHADHI — Agent 1: Inventory Sentinel.

Trigger: Cloud Scheduler every 30 minutes, or a manual API call.
Gemini:  none — pure Python thresholds.

Per docs/AGENTS_SPEC.md Agent 1, for every health center:
    1. read current_stock / maximum_capacity from the inventory collection
    2. stock_percentage = current_stock / maximum_capacity * 100
    3. classify urgency: CRITICAL <15%, LOW <30%, MONITOR <50%, OK >=50%
    4. any CRITICAL or LOW item -> sentinel_alerts document + Pub/Sub message
    5. refresh the center's status.last_checked

Every message carries cycle_id and district_alert_count so the Forecast Agent
can tell when a district's centers have all reported in and outbreak detection
can run once across the whole district rather than once per center.
"""

import uuid
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from config import settings
from models.inventory import InventoryItem
from utils.logger import get_logger

from agents.base_agent import BaseAgent

log = get_logger(__name__)

TOPIC_SENTINEL_ALERTS = "sentinel-alerts"
ALERT_URGENCIES = ("CRITICAL", "LOW")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def classify_urgency(stock_percentage: float) -> str:
    """Thresholds from docs/AGENTS_SPEC.md, tunable via settings."""
    if stock_percentage < settings.critical_threshold_percentage:
        return "CRITICAL"
    if stock_percentage < settings.low_threshold_percentage:
        return "LOW"
    if stock_percentage < 50:
        return "MONITOR"
    return "OK"


def _overall_status(critical_count: int, low_count: int, monitor_count: int) -> str:
    if critical_count:
        return "CRITICAL"
    if low_count:
        return "LOW"
    if monitor_count:
        return "MODERATE"
    return "GOOD"


class InventorySentinelAgent(BaseAgent):
    """Scans every center's inventory and raises threshold alerts."""

    name = "SENTINEL"
    action = "scan_all_centers"
    publishes_to = TOPIC_SENTINEL_ALERTS
    subscribes_to = None

    # ────────────────────────── public entrypoint ──────────────────────

    async def scan_all_centers(
        self, district: Optional[str] = None, cycle_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Cloud Scheduler / manual entrypoint. Runs one full sentinel cycle.

        `cycle_id` lets a caller (the /internal/run-sentinel route) mint the id
        up front so it can return it before the cycle finishes.
        """
        return await self.run(None, {"district": district, "cycle_id": cycle_id})

    # ─────────────────────────────── work ──────────────────────────────

    async def process(
        self, center_id: Optional[str], payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        district = payload.get("district")
        cycle_id = payload.get("cycle_id") or f"cycle_{uuid.uuid4().hex[:12]}"
        started_at = _utc_now_iso()

        centers = await self.firestore.get_all_health_centers(district=district)
        self.log.info(
            "sentinel_cycle_started",
            cycle_id=cycle_id,
            district=district or "ALL",
            centers=len(centers),
        )

        # Pass 1: classify every center's inventory. Nothing is published yet —
        # district_alert_count has to be known before the first message goes out.
        scanned: List[Dict[str, Any]] = []
        no_data_centers: List[str] = []

        for center in centers:
            try:
                items = await self.firestore.get_inventory_for_center(center.id)
            except Exception as exc:
                # Spec: a failed Firestore read skips this center, never the cycle.
                self.log.error(
                    "sentinel_center_read_failed",
                    cycle_id=cycle_id,
                    center_id=center.id,
                    error_type=type(exc).__name__,
                    error=str(exc),
                )
                continue

            if not items:
                no_data_centers.append(center.id)
                self.log.warning(
                    "sentinel_center_no_data", cycle_id=cycle_id, center_id=center.id
                )
                continue

            scanned.append(self._classify_center(center, items))

        alerting = [entry for entry in scanned if entry["critical_items"] or entry["low_items"]]

        alerts_per_district: Dict[str, int] = defaultdict(int)
        for entry in alerting:
            alerts_per_district[entry["district"]] += 1

        # Pass 2: persist + publish.
        published: List[Dict[str, Any]] = []
        for entry in alerting:
            try:
                message = self._build_message(
                    entry, cycle_id, alerts_per_district[entry["district"]]
                )
                alert_id = await self.firestore.create_sentinel_alert(
                    {
                        "cycle_id": cycle_id,
                        "center_id": entry["center_id"],
                        "center_name": entry["center_name"],
                        "district": entry["district"],
                        "total_critical": message["total_critical"],
                        "total_low": message["total_low"],
                        "critical_items": message["critical_items"],
                        "low_items": message["low_items"],
                    }
                )
                message["sentinel_alert_id"] = alert_id
                message_id = await self.publish(message)
                published.append(
                    {
                        "center_id": entry["center_id"],
                        "message_id": message_id,
                        "sentinel_alert_id": alert_id,
                        "total_critical": message["total_critical"],
                        "total_low": message["total_low"],
                    }
                )
                self.log.info(
                    "sentinel_alert_published",
                    cycle_id=cycle_id,
                    center_id=entry["center_id"],
                    center_name=entry["center_name"],
                    total_critical=message["total_critical"],
                    total_low=message["total_low"],
                    message_id=message_id,
                )
            except Exception as exc:
                self.log.error(
                    "sentinel_publish_failed",
                    cycle_id=cycle_id,
                    center_id=entry["center_id"],
                    error_type=type(exc).__name__,
                    error=str(exc),
                )

        # Step 5: refresh status.last_checked on every center that was scanned.
        for entry in scanned:
            try:
                await self.firestore.update_health_center_status(
                    entry["center_id"],
                    {
                        "last_checked": started_at,
                        "overall_stock_status": entry["overall_stock_status"],
                        "critical_items_count": len(entry["critical_items"]),
                        "low_items_count": len(entry["low_items"]),
                    },
                )
            except Exception as exc:
                self.log.warning(
                    "sentinel_status_update_failed",
                    cycle_id=cycle_id,
                    center_id=entry["center_id"],
                    error_type=type(exc).__name__,
                    error=str(exc),
                )

        result = {
            "cycle_id": cycle_id,
            "district": district or "ALL",
            "centers_scanned": len(scanned),
            "centers_alerting": len(alerting),
            "centers_no_data": no_data_centers,
            "total_critical_items": sum(len(e["critical_items"]) for e in scanned),
            "total_low_items": sum(len(e["low_items"]) for e in scanned),
            "alerts_per_district": dict(alerts_per_district),
            "published": published,
            "started_at": started_at,
            "completed_at": _utc_now_iso(),
        }
        self.log.info("sentinel_cycle_complete", **{
            k: v for k, v in result.items() if k not in ("published", "centers_no_data")
        })
        return result

    # ───────────────────────────── helpers ─────────────────────────────

    def _classify_center(self, center, items: List[InventoryItem]) -> Dict[str, Any]:
        critical_items: List[Dict[str, Any]] = []
        low_items: List[Dict[str, Any]] = []
        monitor_count = 0

        for item in items:
            stock_percentage = (
                item.current_stock / item.maximum_capacity * 100
                if item.maximum_capacity
                else 0.0
            )
            urgency = classify_urgency(stock_percentage)
            if urgency == "MONITOR":
                monitor_count += 1
            if urgency not in ALERT_URGENCIES:
                continue

            entry = {
                "medicine_id": item.medicine_id,
                "medicine_name": item.medicine_name,
                "current_stock": item.current_stock,
                "minimum_threshold": item.minimum_threshold,
                "maximum_capacity": item.maximum_capacity,
                "stock_percentage": round(stock_percentage, 1),
                "urgency": urgency,
                # Consumption fields ride along so DQMS can validate and the
                # Forecast Agent can build prompts without re-reading inventory.
                "opening_stock": item.opening_stock_today,
                "daily_consumption": item.daily_consumption_today,
                "seven_day_avg_consumption": item.seven_day_avg_consumption,
                "thirty_day_avg_consumption": item.thirty_day_avg_consumption,
                "consumption_ratio": item.consumption_ratio,
                "anomaly_flag": item.anomaly_flag,
                "anomaly_ratio": item.anomaly_ratio,
                "last_updated": item.last_updated,
            }
            (critical_items if urgency == "CRITICAL" else low_items).append(entry)

        return {
            "center_id": center.id,
            "center_name": center.name,
            "center_type": center.type,
            "district": center.district,
            "subdistrict": center.subdistrict,
            "critical_items": critical_items,
            "low_items": low_items,
            "overall_stock_status": _overall_status(
                len(critical_items), len(low_items), monitor_count
            ),
        }

    @staticmethod
    def _build_message(
        entry: Dict[str, Any], cycle_id: str, district_alert_count: int
    ) -> Dict[str, Any]:
        return {
            "cycle_id": cycle_id,
            "center_id": entry["center_id"],
            "center_name": entry["center_name"],
            "center_type": entry["center_type"],
            "district": entry["district"],
            "subdistrict": entry["subdistrict"],
            "district_alert_count": district_alert_count,
            "critical_items": entry["critical_items"],
            "low_items": entry["low_items"],
            "total_critical": len(entry["critical_items"]),
            "total_low": len(entry["low_items"]),
            "timestamp": _utc_now_iso(),
            "action": "VALIDATION_AND_FORECAST_REQUIRED",
        }
