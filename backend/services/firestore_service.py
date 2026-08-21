"""AUSHADHI — Firestore data access layer.

Single async service wrapping google-cloud-firestore's AsyncClient. Every
read returns a Pydantic model (or None); every write takes a Pydantic model
and calls its own to_firestore_dict().

Collection layout (docs/DATABASE_SCHEMA.md):
    health_centers/{center_id}
    inventory/{center_id}_{medicine_id}                  <-- flat collection
    medicines/{medicine_id}
    consumption_records/{doc_id}
    outbreak_alerts/{doc_id}
    purchase_orders/{doc_id}
    agent_logs/{doc_id}
    warehouses/{warehouse_id}

Inventory is a flat top-level collection keyed `{center_id}_{medicine_id}`,
matching scripts/seed_firestore.py, so cross-center urgency filtering is a
plain where() query with no composite index required.
"""

import time
import uuid
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any, Dict, List, Optional

from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter

from config import settings
from models.agent_log import AgentLog, AgentName, AgentStatus
from models.consumption_record import ConsumptionRecord
from models.health_center import HealthCenter
from models.inventory import InventoryItem, Urgency
from models.medicine import Medicine
from models.outbreak import OutbreakAlert, OutbreakStatus
from models.purchase_order import POPriority, POStatus, PurchaseOrder
from models.warehouse import Warehouse
from utils.logger import get_logger
from utils.retry import retry

log = get_logger(__name__)

# Firestore transient failures resolve much faster than Gemini 503s, so this
# uses a shorter backoff than the retry decorator's Gemini-tuned defaults.
firestore_retry = retry(max_attempts=3, initial_delay=1.0, backoff_factor=2.0, max_delay=8.0)

COLL_HEALTH_CENTERS = "health_centers"
COLL_INVENTORY = "inventory"
COLL_MEDICINES = "medicines"
COLL_CONSUMPTION = "consumption_records"
COLL_OUTBREAKS = "outbreak_alerts"
COLL_PURCHASE_ORDERS = "purchase_orders"
COLL_AGENT_LOGS = "agent_logs"
COLL_WAREHOUSES = "warehouses"
COLL_SENTINEL_ALERTS = "sentinel_alerts"
COLL_NOTIFICATIONS = "notifications"


def _utc_now_iso() -> str:
    """ISO 8601 UTC timestamp string, matching the schema's timestamp format."""
    return datetime.now(timezone.utc).isoformat()


class FirestoreService:
    """Async Firestore access for every AUSHADHI collection."""

    def __init__(self, client: Optional[firestore.AsyncClient] = None) -> None:
        self._db = client or firestore.AsyncClient(
            project=settings.google_cloud_project,
            database=settings.firestore_database_id,
        )
        log.info(
            "firestore_service_initialized",
            project=settings.google_cloud_project,
            database=settings.firestore_database_id,
        )

    @property
    def db(self) -> firestore.AsyncClient:
        return self._db

    # ───────────────────────── HEALTH CENTERS ─────────────────────────

    @firestore_retry
    async def get_health_center(self, center_id: str) -> Optional[HealthCenter]:
        started = time.perf_counter()
        snap = await self._db.collection(COLL_HEALTH_CENTERS).document(center_id).get()
        duration_ms = int((time.perf_counter() - started) * 1000)

        if not snap.exists:
            log.warning(
                "firestore_doc_not_found",
                collection=COLL_HEALTH_CENTERS,
                doc_id=center_id,
                duration_ms=duration_ms,
            )
            return None

        log.info(
            "firestore_read",
            collection=COLL_HEALTH_CENTERS,
            doc_id=center_id,
            duration_ms=duration_ms,
        )
        return HealthCenter(**snap.to_dict())

    @firestore_retry
    async def get_all_health_centers(self, district: Optional[str] = None) -> List[HealthCenter]:
        started = time.perf_counter()
        query = self._db.collection(COLL_HEALTH_CENTERS)
        if district:
            query = query.where(filter=FieldFilter("district", "==", district))

        centers: List[HealthCenter] = []
        async for snap in query.stream():
            try:
                centers.append(HealthCenter(**snap.to_dict()))
            except Exception as exc:
                log.error(
                    "firestore_model_validation_failed",
                    collection=COLL_HEALTH_CENTERS,
                    doc_id=snap.id,
                    error=str(exc),
                )

        duration_ms = int((time.perf_counter() - started) * 1000)
        log.info(
            "firestore_query",
            collection=COLL_HEALTH_CENTERS,
            district=district,
            count=len(centers),
            duration_ms=duration_ms,
        )
        return centers

    @firestore_retry
    async def update_health_center_status(
        self, center_id: str, status_dict: Dict[str, Any]
    ) -> None:
        started = time.perf_counter()
        updates = {
            **{f"status.{key}": value for key, value in status_dict.items()},
            "updated_at": _utc_now_iso(),
        }
        await self._db.collection(COLL_HEALTH_CENTERS).document(center_id).update(updates)
        log.info(
            "firestore_update",
            collection=COLL_HEALTH_CENTERS,
            doc_id=center_id,
            fields=sorted(status_dict.keys()),
            duration_ms=int((time.perf_counter() - started) * 1000),
        )

    # ─────────────────────────── INVENTORY ────────────────────────────
    # Flat top-level collection: inventory/{center_id}_{medicine_id}
    # Matches the doc_id convention written by scripts/seed_firestore.py.

    @staticmethod
    def _inventory_doc_id(center_id: str, medicine_id: str) -> str:
        return f"{center_id}_{medicine_id}"

    def _inventory_ref(self, center_id: str, medicine_id: str):
        return self._db.collection(COLL_INVENTORY).document(
            self._inventory_doc_id(center_id, medicine_id)
        )

    @firestore_retry
    async def get_inventory_item(
        self, center_id: str, medicine_id: str
    ) -> Optional[InventoryItem]:
        """Direct document lookup at inventory/{center_id}_{medicine_id}."""
        started = time.perf_counter()
        doc_id = self._inventory_doc_id(center_id, medicine_id)
        snap = await self._inventory_ref(center_id, medicine_id).get()
        duration_ms = int((time.perf_counter() - started) * 1000)

        if not snap.exists:
            log.warning(
                "firestore_doc_not_found",
                collection=COLL_INVENTORY,
                doc_id=doc_id,
                duration_ms=duration_ms,
            )
            return None

        log.info(
            "firestore_read",
            collection=COLL_INVENTORY,
            doc_id=doc_id,
            duration_ms=duration_ms,
        )
        return InventoryItem(**snap.to_dict())

    @firestore_retry
    async def get_inventory_by_urgency(
        self, urgency: Urgency, district: Optional[str] = None
    ) -> List[InventoryItem]:
        """Cross-center urgency query over the flat `inventory` collection.

        District filtering is applied in-process by cross-referencing
        `health_centers`, because `district` lives on the health center
        document, not on the inventory document.
        """
        started = time.perf_counter()

        allowed_center_ids: Optional[set] = None
        if district:
            centers = await self.get_all_health_centers(district=district)
            allowed_center_ids = {center.id for center in centers}

        query = self._db.collection(COLL_INVENTORY).where(
            filter=FieldFilter("urgency", "==", urgency)
        )

        items: List[InventoryItem] = []
        async for snap in query.stream():
            data = snap.to_dict()
            if allowed_center_ids is not None and data.get("center_id") not in allowed_center_ids:
                continue
            try:
                items.append(InventoryItem(**data))
            except Exception as exc:
                log.error(
                    "firestore_model_validation_failed",
                    collection=COLL_INVENTORY,
                    doc_id=snap.id,
                    error=str(exc),
                )

        duration_ms = int((time.perf_counter() - started) * 1000)
        log.info(
            "firestore_query",
            collection=COLL_INVENTORY,
            urgency=urgency,
            district=district,
            count=len(items),
            duration_ms=duration_ms,
        )
        return items

    @firestore_retry
    async def get_inventory_for_center(self, center_id: str) -> List[InventoryItem]:
        """Every inventory line for one center — the Sentinel Agent's per-center scan."""
        started = time.perf_counter()
        query = self._db.collection(COLL_INVENTORY).where(
            filter=FieldFilter("center_id", "==", center_id)
        )

        items: List[InventoryItem] = []
        async for snap in query.stream():
            try:
                items.append(InventoryItem(**snap.to_dict()))
            except Exception as exc:
                log.error(
                    "firestore_model_validation_failed",
                    collection=COLL_INVENTORY,
                    doc_id=snap.id,
                    error=str(exc),
                )

        log.info(
            "firestore_query",
            collection=COLL_INVENTORY,
            center_id=center_id,
            count=len(items),
            duration_ms=int((time.perf_counter() - started) * 1000),
        )
        return items

    @firestore_retry
    async def update_inventory_item(
        self, center_id: str, medicine_id: str, updates_dict: Dict[str, Any]
    ) -> None:
        started = time.perf_counter()
        updates = {**updates_dict, "updated_at": _utc_now_iso()}
        await self._inventory_ref(center_id, medicine_id).update(updates)
        log.info(
            "firestore_update",
            collection=COLL_INVENTORY,
            doc_id=self._inventory_doc_id(center_id, medicine_id),
            fields=sorted(updates_dict.keys()),
            duration_ms=int((time.perf_counter() - started) * 1000),
        )

    # ────────────────────────── OUTBREAK ALERTS ───────────────────────

    @firestore_retry
    async def create_outbreak_alert(self, alert: OutbreakAlert) -> str:
        started = time.perf_counter()
        doc_id = alert.id or str(uuid.uuid4())
        payload = alert.to_firestore_dict()
        payload["id"] = doc_id
        await self._db.collection(COLL_OUTBREAKS).document(doc_id).set(payload)
        log.info(
            "firestore_create",
            collection=COLL_OUTBREAKS,
            doc_id=doc_id,
            risk_level=alert.risk_level,
            affected_centers=len(alert.affected_center_ids),
            duration_ms=int((time.perf_counter() - started) * 1000),
        )
        return doc_id

    @firestore_retry
    async def get_active_outbreaks(self, district: Optional[str] = None) -> List[OutbreakAlert]:
        """ACTIVE + UNDER_RESPONSE alerts, newest first."""
        started = time.perf_counter()
        query = self._db.collection(COLL_OUTBREAKS).where(
            filter=FieldFilter("status", "in", ["ACTIVE", "UNDER_RESPONSE"])
        )
        if district:
            query = query.where(filter=FieldFilter("district", "==", district))
        query = query.order_by("created_at", direction=firestore.Query.DESCENDING)

        alerts: List[OutbreakAlert] = []
        async for snap in query.stream():
            try:
                alerts.append(OutbreakAlert(**snap.to_dict()))
            except Exception as exc:
                log.error(
                    "firestore_model_validation_failed",
                    collection=COLL_OUTBREAKS,
                    doc_id=snap.id,
                    error=str(exc),
                )

        log.info(
            "firestore_query",
            collection=COLL_OUTBREAKS,
            district=district,
            count=len(alerts),
            duration_ms=int((time.perf_counter() - started) * 1000),
        )
        return alerts

    @firestore_retry
    async def update_outbreak_status(
        self, alert_id: str, status: OutbreakStatus, **kwargs: Any
    ) -> None:
        """Update alert status; extra kwargs (acknowledged_by, resolution_notes,
        linked_po_ids, ...) are written as-is."""
        started = time.perf_counter()
        updates: Dict[str, Any] = {"status": status, "updated_at": _utc_now_iso(), **kwargs}
        await self._db.collection(COLL_OUTBREAKS).document(alert_id).update(updates)
        log.info(
            "firestore_update",
            collection=COLL_OUTBREAKS,
            doc_id=alert_id,
            status=status,
            fields=sorted(kwargs.keys()),
            duration_ms=int((time.perf_counter() - started) * 1000),
        )

    # ───────────────────────── PURCHASE ORDERS ────────────────────────

    @firestore_retry
    async def create_purchase_order(self, po: PurchaseOrder) -> str:
        started = time.perf_counter()
        doc_id = po.id or str(uuid.uuid4())
        payload = po.to_firestore_dict()
        payload["id"] = doc_id
        await self._db.collection(COLL_PURCHASE_ORDERS).document(doc_id).set(payload)
        log.info(
            "firestore_create",
            collection=COLL_PURCHASE_ORDERS,
            doc_id=doc_id,
            po_number=po.po_number,
            priority=po.priority,
            total_cost_inr=po.total_cost_inr,
            duration_ms=int((time.perf_counter() - started) * 1000),
        )
        return doc_id

    @firestore_retry
    async def get_purchase_orders(
        self,
        status: Optional[POStatus] = None,
        priority: Optional[POPriority] = None,
    ) -> List[PurchaseOrder]:
        started = time.perf_counter()
        query = self._db.collection(COLL_PURCHASE_ORDERS)
        if status:
            query = query.where(filter=FieldFilter("status", "==", status))
        if priority:
            query = query.where(filter=FieldFilter("priority", "==", priority))
        query = query.order_by("created_at", direction=firestore.Query.DESCENDING)

        orders: List[PurchaseOrder] = []
        async for snap in query.stream():
            try:
                orders.append(PurchaseOrder(**snap.to_dict()))
            except Exception as exc:
                log.error(
                    "firestore_model_validation_failed",
                    collection=COLL_PURCHASE_ORDERS,
                    doc_id=snap.id,
                    error=str(exc),
                )

        log.info(
            "firestore_query",
            collection=COLL_PURCHASE_ORDERS,
            status=status,
            priority=priority,
            count=len(orders),
            duration_ms=int((time.perf_counter() - started) * 1000),
        )
        return orders

    @firestore_retry
    async def update_po_status(self, po_id: str, status: POStatus, **kwargs: Any) -> None:
        """Update PO status; extra kwargs (approved_by, dispatched_at, ...) written as-is."""
        started = time.perf_counter()
        updates: Dict[str, Any] = {"status": status, "updated_at": _utc_now_iso(), **kwargs}
        await self._db.collection(COLL_PURCHASE_ORDERS).document(po_id).update(updates)
        log.info(
            "firestore_update",
            collection=COLL_PURCHASE_ORDERS,
            doc_id=po_id,
            status=status,
            fields=sorted(kwargs.keys()),
            duration_ms=int((time.perf_counter() - started) * 1000),
        )

    # ─────────────────────────── AGENT LOGS ───────────────────────────

    @firestore_retry
    async def log_agent_start(
        self,
        agent_name: AgentName,
        center_id: Optional[str],
        action: str,
        input_data: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Write a STARTED agent log and return its document id."""
        started = time.perf_counter()
        doc_ref = self._db.collection(COLL_AGENT_LOGS).document()
        entry = AgentLog(
            id=doc_ref.id,
            center_id=center_id,
            agent_name=agent_name,
            action=action,
            status="STARTED",
            input=input_data or {},
            created_at=_utc_now_iso(),
        )
        await doc_ref.set(entry.to_firestore_dict())
        log.info(
            "agent_log_started",
            collection=COLL_AGENT_LOGS,
            doc_id=doc_ref.id,
            agent=agent_name,
            action=action,
            center_id=center_id,
            duration_ms=int((time.perf_counter() - started) * 1000),
        )
        return doc_ref.id

    @firestore_retry
    async def log_agent_complete(
        self, log_id: str, output_data: Dict[str, Any], duration_ms: int
    ) -> None:
        started = time.perf_counter()
        await self._db.collection(COLL_AGENT_LOGS).document(log_id).update(
            {
                "status": "COMPLETED",
                "output": output_data,
                "duration_ms": duration_ms,
                "completed_at": _utc_now_iso(),
            }
        )
        log.info(
            "agent_log_completed",
            collection=COLL_AGENT_LOGS,
            doc_id=log_id,
            agent_duration_ms=duration_ms,
            duration_ms=int((time.perf_counter() - started) * 1000),
        )

    @firestore_retry
    async def log_agent_failure(
        self, log_id: str, error_message: str, retry_count: int = 0
    ) -> None:
        started = time.perf_counter()
        await self._db.collection(COLL_AGENT_LOGS).document(log_id).update(
            {
                "status": "FAILED",
                "error": {"message": error_message, "retry_count": retry_count},
                "completed_at": _utc_now_iso(),
            }
        )
        log.error(
            "agent_log_failed",
            collection=COLL_AGENT_LOGS,
            doc_id=log_id,
            retry_count=retry_count,
            agent_error=error_message,
            duration_ms=int((time.perf_counter() - started) * 1000),
        )

    # ─────────────────────────── MEDICINES ────────────────────────────

    @firestore_retry
    async def get_all_medicines(self) -> List[Medicine]:
        started = time.perf_counter()
        medicines: List[Medicine] = []
        async for snap in self._db.collection(COLL_MEDICINES).stream():
            try:
                medicines.append(Medicine(**snap.to_dict()))
            except Exception as exc:
                log.error(
                    "firestore_model_validation_failed",
                    collection=COLL_MEDICINES,
                    doc_id=snap.id,
                    error=str(exc),
                )

        log.info(
            "firestore_query",
            collection=COLL_MEDICINES,
            count=len(medicines),
            duration_ms=int((time.perf_counter() - started) * 1000),
        )
        return medicines

    @firestore_retry
    async def get_medicine(self, medicine_id: str) -> Optional[Medicine]:
        started = time.perf_counter()
        snap = await self._db.collection(COLL_MEDICINES).document(medicine_id).get()
        duration_ms = int((time.perf_counter() - started) * 1000)

        if not snap.exists:
            log.warning(
                "firestore_doc_not_found",
                collection=COLL_MEDICINES,
                doc_id=medicine_id,
                duration_ms=duration_ms,
            )
            return None

        log.info(
            "firestore_read",
            collection=COLL_MEDICINES,
            doc_id=medicine_id,
            duration_ms=duration_ms,
        )
        return Medicine(**snap.to_dict())

    # ────────────────────── CONSUMPTION RECORDS ───────────────────────

    @firestore_retry
    async def get_consumption_history(
        self, center_id: str, medicine_id: str, days: int = 7
    ) -> List[ConsumptionRecord]:
        """Most recent `days` consumption records, newest first."""
        started = time.perf_counter()
        query = (
            self._db.collection(COLL_CONSUMPTION)
            .where(filter=FieldFilter("center_id", "==", center_id))
            .where(filter=FieldFilter("medicine_id", "==", medicine_id))
            .order_by("report_date", direction=firestore.Query.DESCENDING)
            .limit(days)
        )

        records: List[ConsumptionRecord] = []
        async for snap in query.stream():
            try:
                records.append(ConsumptionRecord(**snap.to_dict()))
            except Exception as exc:
                log.error(
                    "firestore_model_validation_failed",
                    collection=COLL_CONSUMPTION,
                    doc_id=snap.id,
                    error=str(exc),
                )

        log.info(
            "firestore_query",
            collection=COLL_CONSUMPTION,
            center_id=center_id,
            medicine_id=medicine_id,
            days=days,
            count=len(records),
            duration_ms=int((time.perf_counter() - started) * 1000),
        )
        return records

    # ─────────────────────────── WAREHOUSES ───────────────────────────

    @firestore_retry
    async def get_all_warehouses(self) -> List[Warehouse]:
        started = time.perf_counter()
        warehouses: List[Warehouse] = []
        async for snap in self._db.collection(COLL_WAREHOUSES).stream():
            try:
                warehouses.append(Warehouse(**snap.to_dict()))
            except Exception as exc:
                log.error(
                    "firestore_model_validation_failed",
                    collection=COLL_WAREHOUSES,
                    doc_id=snap.id,
                    error=str(exc),
                )

        log.info(
            "firestore_query",
            collection=COLL_WAREHOUSES,
            count=len(warehouses),
            duration_ms=int((time.perf_counter() - started) * 1000),
        )
        return warehouses

    @firestore_retry
    async def get_warehouse(self, warehouse_id: str) -> Optional[Warehouse]:
        started = time.perf_counter()
        snap = await self._db.collection(COLL_WAREHOUSES).document(warehouse_id).get()
        duration_ms = int((time.perf_counter() - started) * 1000)

        if not snap.exists:
            log.warning(
                "firestore_doc_not_found",
                collection=COLL_WAREHOUSES,
                doc_id=warehouse_id,
                duration_ms=duration_ms,
            )
            return None

        log.info(
            "firestore_read",
            collection=COLL_WAREHOUSES,
            doc_id=warehouse_id,
            duration_ms=duration_ms,
        )
        return Warehouse(**snap.to_dict())

    # ──────────────────── SENTINEL ALERTS / NOTIFICATIONS ─────────────
    # Plain dict documents — neither collection has a model in models/.

    @firestore_retry
    async def create_sentinel_alert(self, alert: Dict[str, Any]) -> str:
        started = time.perf_counter()
        doc_ref = self._db.collection(COLL_SENTINEL_ALERTS).document()
        payload = {**alert, "id": doc_ref.id, "created_at": _utc_now_iso()}
        await doc_ref.set(payload)
        log.info(
            "firestore_create",
            collection=COLL_SENTINEL_ALERTS,
            doc_id=doc_ref.id,
            center_id=alert.get("center_id"),
            duration_ms=int((time.perf_counter() - started) * 1000),
        )
        return doc_ref.id

    @firestore_retry
    async def create_notification(self, notification: Dict[str, Any]) -> str:
        started = time.perf_counter()
        doc_ref = self._db.collection(COLL_NOTIFICATIONS).document()
        payload = {**notification, "id": doc_ref.id, "created_at": _utc_now_iso()}
        await doc_ref.set(payload)
        log.info(
            "firestore_create",
            collection=COLL_NOTIFICATIONS,
            doc_id=doc_ref.id,
            notification_type=notification.get("type"),
            recipient=notification.get("recipient"),
            duration_ms=int((time.perf_counter() - started) * 1000),
        )
        return doc_ref.id

    async def close(self) -> None:
        """Release the underlying gRPC channel (call on app shutdown)."""
        self._db.close()
        log.info("firestore_service_closed")


@lru_cache
def get_firestore_service() -> FirestoreService:
    """Cached singleton, same style as config.get_settings()."""
    return FirestoreService()
