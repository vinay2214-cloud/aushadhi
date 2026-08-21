"""AUSHADHI — Agent 4: Procurement.

Trigger: subscribes to aushadhi-forecast-complete.
Gemini:  none — deterministic routing and PO assembly.

Nearest-warehouse routing is the CrisisRoute logic from docs/AGENTS_SPEC.md
Agent 4: haversine distance from the health center to every warehouse holding
enough stock, delivery estimated at 60 km/h plus two hours of loading, nearest
wins. Line items routed to the same warehouse are batched onto one purchase
order; a medicine no warehouse can fill is reported as unroutable rather than
silently dropped.
"""

import uuid
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter
from haversine import Unit, haversine

from models.purchase_order import PurchaseOrder, PurchaseOrderLineItem
from utils.logger import get_logger

from agents.base_agent import BaseAgent

log = get_logger(__name__)

TOPIC_PROCURED = "procured"

#: Urgencies from the Forecast Agent that trigger an automatic PO.
ORDER_URGENCIES = ("CRITICAL", "HIGH")
PRIORITY_RANK = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}

AVERAGE_SPEED_KMH = 60.0
LOADING_TIME_HOURS = 2.0


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ProcurementAgent(BaseAgent):
    """Turns forecast urgencies into routed, costed purchase orders."""

    name = "PROCUREMENT"
    action = "generate_purchase_orders"
    publishes_to = TOPIC_PROCURED
    subscribes_to = "forecast-complete-sub"

    async def process(
        self, center_id: Optional[str], payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        center_id = center_id or payload.get("center_id")
        forecasts = payload.get("forecasts", [])
        outbreak = payload.get("outbreak") or {}

        orderable = [
            f
            for f in forecasts
            if (f.get("forecast") or {}).get("reorder_urgency") in ORDER_URGENCIES
        ]
        if not orderable:
            self.log.info(
                "procurement_nothing_to_order",
                center_id=center_id,
                forecasts=len(forecasts),
            )
            return {"center_id": center_id, "purchase_orders": [], "reason": "NO_URGENT_ITEMS"}

        center = await self.firestore.get_health_center(center_id)
        if center is None:
            raise ValueError(f"health center {center_id} not found in Firestore")
        warehouses = await self.firestore.get_all_warehouses()

        # Route every item first, then batch by warehouse so one delivery run
        # carries as many of a center's medicines as it can.
        routed: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        unroutable: List[Dict[str, Any]] = []

        for item in orderable:
            forecast = item["forecast"]
            quantity = int(forecast.get("recommended_order_quantity") or 0)
            if quantity <= 0:
                continue

            warehouse = self.find_nearest_warehouse(center, item["medicine_id"], quantity, warehouses)
            if warehouse is None:
                unroutable.append(
                    {
                        "medicine_id": item["medicine_id"],
                        "medicine_name": item["medicine_name"],
                        "requested_quantity": quantity,
                        "reason": "NO_WAREHOUSE_WITH_SUFFICIENT_STOCK",
                    }
                )
                self.log.warning(
                    "procurement_unroutable_item",
                    center_id=center_id,
                    medicine_id=item["medicine_id"],
                    requested_quantity=quantity,
                )
                continue

            routed[warehouse["id"]].append({"item": item, "warehouse": warehouse, "quantity": quantity})

        created: List[Dict[str, Any]] = []
        for warehouse_id, entries in routed.items():
            po_summary = await self._create_purchase_order(
                center=center,
                warehouse=entries[0]["warehouse"],
                entries=entries,
                outbreak=outbreak,
            )
            created.append(po_summary)

            message = {
                "cycle_id": payload.get("cycle_id"),
                "center_id": center.id,
                "center_name": center.name,
                "center_type": center.type,
                "district": center.district,
                "subdistrict": center.subdistrict,
                "medical_officer": center.medical_officer,
                "contact_email": center.contact_email,
                "purchase_order": po_summary,
                "outbreak": outbreak,
                "action": "NOTIFICATION_REQUIRED",
            }
            message_id = await self.publish(message)
            self.log.info(
                "procurement_po_published",
                center_id=center.id,
                po_number=po_summary["po_number"],
                warehouse_id=warehouse_id,
                total_cost_inr=po_summary["total_cost_inr"],
                message_id=message_id,
            )

        return {
            "center_id": center_id,
            "purchase_orders": created,
            "unroutable_items": unroutable,
            "outbreak_linked": bool(outbreak.get("outbreak_alert_id")),
        }

    # ─────────────────────── routing (from CrisisRoute) ─────────────────

    def find_nearest_warehouse(
        self, center, medicine_id: str, quantity: int, warehouses: List[Any]
    ) -> Optional[Dict[str, Any]]:
        """Nearest warehouse holding at least `quantity` of `medicine_id`."""
        scored: List[Dict[str, Any]] = []
        for warehouse in warehouses:
            stock = next(
                (m for m in warehouse.available_medicines if m.medicine_id == medicine_id),
                None,
            )
            if stock is None or stock.available_quantity < quantity:
                continue

            distance_km = haversine(
                (center.location.lat, center.location.lng),
                (warehouse.location.lat, warehouse.location.lng),
                unit=Unit.KILOMETERS,
            )
            scored.append(
                {
                    "id": warehouse.id,
                    "name": warehouse.name,
                    "district": warehouse.district,
                    "address": warehouse.location.address,
                    "phone": warehouse.contact.phone,
                    "distance_km": round(distance_km, 1),
                    "eta_hours": round(distance_km / AVERAGE_SPEED_KMH + LOADING_TIME_HOURS, 1),
                    "available_quantity": stock.available_quantity,
                }
            )

        if not scored:
            return None
        return min(scored, key=lambda w: w["distance_km"])

    # ──────────────────────────── PO assembly ──────────────────────────

    async def _create_purchase_order(
        self,
        center,
        warehouse: Dict[str, Any],
        entries: List[Dict[str, Any]],
        outbreak: Dict[str, Any],
    ) -> Dict[str, Any]:
        now = _utc_now_iso()
        line_items: List[PurchaseOrderLineItem] = []

        for entry in entries:
            item = entry["item"]
            forecast = item["forecast"]
            quantity = entry["quantity"]
            unit_cost = float(item.get("unit_cost_inr") or 0.0)
            line_items.append(
                PurchaseOrderLineItem(
                    medicine_id=item["medicine_id"],
                    medicine_name=item["medicine_name"],
                    requested_quantity=quantity,
                    unit=item.get("unit") or "units",
                    unit_cost_inr=unit_cost,
                    total_cost_inr=round(unit_cost * quantity, 2),
                    urgency=forecast.get("reorder_urgency", "MEDIUM"),
                    days_until_stockout=int(
                        forecast.get("days_until_stockout_at_current_trend") or 0
                    ),
                )
            )

        priority = min(
            (li.urgency for li in line_items),
            key=lambda u: PRIORITY_RANK.get(u, 99),
            default="MEDIUM",
        )
        total_cost = round(sum(li.total_cost_inr for li in line_items), 2)
        po_number = await self._next_po_number()
        outbreak_alert_id = outbreak.get("outbreak_alert_id")
        outbreak_linked = bool(outbreak_alert_id) and bool(outbreak.get("center_affected"))

        po = PurchaseOrder(
            id=f"po_{uuid.uuid4().hex[:12]}",
            po_number=po_number,
            health_center_id=center.id,
            health_center_name=center.name,
            district=center.district,
            warehouse_id=warehouse["id"],
            warehouse_name=warehouse["name"],
            warehouse_distance_km=warehouse["distance_km"],
            estimated_delivery_hours=warehouse["eta_hours"],
            priority=priority,
            line_items=line_items,
            total_cost_inr=total_cost,
            status="PENDING_APPROVAL",
            outbreak_linked=outbreak_linked,
            outbreak_alert_id=outbreak_alert_id if outbreak_linked else None,
            approval_required=True,
            created_at=now,
            updated_at=now,
        )
        po_id = await self.firestore.create_purchase_order(po)

        # Inventory now has stock on the way — record when it should land.
        expected = (
            datetime.now(timezone.utc) + timedelta(hours=warehouse["eta_hours"])
        ).isoformat()
        for line in line_items:
            try:
                await self.firestore.update_inventory_item(
                    center.id,
                    line.medicine_id,
                    {
                        "pending_order_quantity": line.requested_quantity,
                        "expected_stock_date": expected,
                    },
                )
            except Exception as exc:
                self.log.warning(
                    "procurement_inventory_update_failed",
                    center_id=center.id,
                    medicine_id=line.medicine_id,
                    error_type=type(exc).__name__,
                    error=str(exc),
                )

        if outbreak_linked:
            try:
                await self.firestore.update_outbreak_status(
                    outbreak_alert_id,
                    "ACTIVE",
                    linked_po_ids=firestore.ArrayUnion([po_id]),
                )
            except Exception as exc:
                self.log.warning(
                    "procurement_outbreak_link_failed",
                    outbreak_alert_id=outbreak_alert_id,
                    po_id=po_id,
                    error_type=type(exc).__name__,
                    error=str(exc),
                )

        self.log.info(
            "procurement_po_created",
            center_id=center.id,
            po_id=po_id,
            po_number=po_number,
            priority=priority,
            line_items=len(line_items),
            total_cost_inr=total_cost,
            warehouse=warehouse["name"],
            distance_km=warehouse["distance_km"],
            eta_hours=warehouse["eta_hours"],
            outbreak_linked=outbreak_linked,
        )

        return {
            "po_id": po_id,
            "po_number": po_number,
            "priority": priority,
            "status": "PENDING_APPROVAL",
            "warehouse": warehouse,
            "line_items": [li.model_dump() for li in line_items],
            "total_cost_inr": total_cost,
            "estimated_delivery_hours": warehouse["eta_hours"],
            "expected_stock_date": expected,
            "outbreak_linked": outbreak_linked,
            "outbreak_alert_id": outbreak_alert_id if outbreak_linked else None,
            "generated_at": now,
        }

    async def _next_po_number(self) -> str:
        """AUSD-{YYYYMMDD}-{sequence}, sequence counted from today's POs.

        A prefix range scan on po_number is a single-field query, so this needs
        no composite index.
        """
        prefix = f"AUSD-{datetime.now(timezone.utc):%Y%m%d}-"
        try:
            query = (
                self.firestore.db.collection("purchase_orders")
                .where(filter=FieldFilter("po_number", ">=", prefix))
                .where(filter=FieldFilter("po_number", "<", prefix + "￿"))
            )
            count = 0
            async for _ in query.stream():
                count += 1
        except Exception as exc:
            count = 0
            self.log.warning(
                "procurement_po_sequence_fallback",
                error_type=type(exc).__name__,
                error=str(exc),
            )
        return f"{prefix}{count + 1:04d}"
