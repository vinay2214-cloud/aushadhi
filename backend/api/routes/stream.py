"""AUSHADHI — Server-Sent Events feed for the live dashboard.

GET /api/v1/stream?api_key=<key>

EventSource cannot set request headers, so this endpoint authenticates on the
query string (see api/middleware/auth.py).

Three sources feed one asyncio queue:

  * Firestore on_snapshot listeners on outbreak_alerts, purchase_orders and
    inventory. on_snapshot only exists on the SYNCHRONOUS client and fires on a
    background thread, so callbacks hand work back to the event loop with
    call_soon_threadsafe.
  * A 3-second poll of agent_logs, which streams each agent step as it happens.
    A polled read is used rather than a fourth listener because the interesting
    part is ordering by created_at, which snapshots do not give cheaply.
  * A 30-second heartbeat so proxies (and the browser) keep the connection open
    even when the pipeline is quiet.

Events emitted: sentinel_cycle_started, agent_step, inventory_updated,
outbreak_detected, purchase_order_created, pipeline_complete, heartbeat.
"""

import asyncio
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Request
from google.cloud import firestore as sync_firestore
from google.cloud.firestore_v1.base_query import FieldFilter
from sse_starlette.sse import EventSourceResponse

from config import settings
from services.firestore_service import get_firestore_service
from utils.logger import get_logger

log = get_logger(__name__)

router = APIRouter(tags=["stream"])

AGENT_LOG_POLL_SECONDS = 3.0
HEARTBEAT_SECONDS = 30.0
QUEUE_MAX_SIZE = 500
#: Guard against a slow client: drop the connection rather than buffer forever.
QUEUE_FULL_DROP_WARNING_EVERY = 25


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class _EventBus:
    """Bridges Firestore's callback threads into one asyncio queue."""

    def __init__(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop
        self.queue: asyncio.Queue = asyncio.Queue(maxsize=QUEUE_MAX_SIZE)
        self._dropped = 0

    def publish_threadsafe(self, event: str, data: Dict[str, Any]) -> None:
        self._loop.call_soon_threadsafe(self._put, event, data)

    def _put(self, event: str, data: Dict[str, Any]) -> None:
        try:
            self.queue.put_nowait({"event": event, "data": data})
        except asyncio.QueueFull:
            self._dropped += 1
            if self._dropped % QUEUE_FULL_DROP_WARNING_EVERY == 1:
                log.warning("sse_queue_full_dropping", dropped=self._dropped, event=event)

    async def publish(self, event: str, data: Dict[str, Any]) -> None:
        self._put(event, data)


def _outbreak_payload(doc: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": doc.get("id"),
        "district": doc.get("district"),
        "risk_level": doc.get("risk_level"),
        "disease_indicators": doc.get("disease_indicators", []),
        "affected_center_ids": doc.get("affected_center_ids", []),
        "confidence": doc.get("confidence"),
        "outbreak_summary": doc.get("outbreak_summary"),
        "geographic_cluster": doc.get("geographic_cluster"),
        "key_evidence": doc.get("key_evidence", []),
        "status": doc.get("status"),
        "created_at": doc.get("created_at"),
    }


def _po_payload(doc: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": doc.get("id"),
        "po_number": doc.get("po_number"),
        "health_center_id": doc.get("health_center_id"),
        "health_center_name": doc.get("health_center_name"),
        "district": doc.get("district"),
        "priority": doc.get("priority"),
        "status": doc.get("status"),
        "total_cost_inr": doc.get("total_cost_inr"),
        "warehouse_name": doc.get("warehouse_name"),
        "estimated_delivery_hours": doc.get("estimated_delivery_hours"),
        "outbreak_linked": doc.get("outbreak_linked"),
        "outbreak_alert_id": doc.get("outbreak_alert_id"),
        "line_items": doc.get("line_items", []),
        "created_at": doc.get("created_at"),
    }


def _inventory_payload(doc: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "center_id": doc.get("center_id"),
        "medicine_id": doc.get("medicine_id"),
        "medicine_name": doc.get("medicine_name"),
        "current_stock": doc.get("current_stock"),
        "stock_percentage": doc.get("stock_percentage"),
        "urgency": doc.get("urgency"),
        "consumption_ratio": doc.get("consumption_ratio"),
        "anomaly_flag": doc.get("anomaly_flag"),
        "pending_order_quantity": doc.get("pending_order_quantity"),
        "expected_stock_date": doc.get("expected_stock_date"),
        "last_updated": doc.get("last_updated"),
    }


def _agent_step_payload(entry: Dict[str, Any]) -> Dict[str, Any]:
    output = entry.get("output") or {}
    return {
        "log_id": entry.get("id"),
        "agent": entry.get("agent_name"),
        "action": entry.get("action"),
        "status": entry.get("status"),
        "center_id": entry.get("center_id"),
        "duration_ms": entry.get("duration_ms"),
        "cycle_id": (entry.get("input") or {}).get("cycle_id") or output.get("cycle_id"),
        "summary": {
            key: output[key]
            for key in (
                "centers_alerting",
                "forecasts_generated",
                "valid_records",
                "rejected_records",
                "notifications_sent",
                "purchase_orders",
            )
            if key in output
        },
        "created_at": entry.get("created_at"),
        "error": entry.get("error"),
    }


def _start_listeners(bus: _EventBus) -> List[Any]:
    """Attach on_snapshot listeners; returns the watches so they can be closed.

    The first snapshot replays the whole collection as ADDED, which would flood
    a newly connected dashboard with historical rows, so the initial batch for
    each listener is skipped.
    """
    db = sync_firestore.Client(
        project=settings.google_cloud_project, database=settings.firestore_database_id
    )
    seen_first: Dict[str, bool] = {}

    def make_callback(name: str, event: str, payload_fn, change_type: str = "ADDED"):
        def callback(col_snapshot, changes, read_time):
            first = not seen_first.get(name, False)
            seen_first[name] = True
            if first:
                return
            for change in changes:
                # outbreak_detected / purchase_order_created mean a NEW document;
                # an acknowledge or approve is a MODIFIED and must not be
                # replayed as a fresh detection.
                if change.type.name != change_type:
                    continue
                try:
                    bus.publish_threadsafe(event, payload_fn(change.document.to_dict()))
                except Exception as exc:
                    log.error(
                        "sse_listener_callback_failed",
                        listener=name,
                        error_type=type(exc).__name__,
                        error=str(exc),
                    )

        return callback

    watches = [
        db.collection("outbreak_alerts").on_snapshot(
            make_callback("outbreak_alerts", "outbreak_detected", _outbreak_payload)
        ),
        db.collection("purchase_orders").on_snapshot(
            make_callback("purchase_orders", "purchase_order_created", _po_payload)
        ),
        db.collection("inventory").on_snapshot(
            make_callback(
                "inventory", "inventory_updated", _inventory_payload, change_type="MODIFIED"
            )
        ),
    ]
    log.info("sse_listeners_started", listeners=len(watches))
    return watches


async def _poll_agent_logs(bus: _EventBus) -> None:
    """Emit agent_step for each new agent_logs document, every 3 seconds.

    Also derives the two lifecycle events the dashboard needs:
    sentinel_cycle_started (a SENTINEL run begins) and pipeline_complete (an
    ALERT run finishes — the last stage of the chain).
    """
    svc = get_firestore_service()
    cursor = _utc_now_iso()

    while True:
        try:
            query = (
                svc.db.collection("agent_logs")
                .where(filter=FieldFilter("created_at", ">", cursor))
                .order_by("created_at")
                .limit(50)
            )
            entries = [snap.to_dict() async for snap in query.stream()]

            for entry in entries:
                created_at = entry.get("created_at") or ""
                if created_at > cursor:
                    cursor = created_at

                await bus.publish("agent_step", _agent_step_payload(entry))

                agent = entry.get("agent_name")
                status = entry.get("status")
                if agent == "SENTINEL" and status == "STARTED":
                    await bus.publish(
                        "sentinel_cycle_started",
                        {
                            "cycle_id": (entry.get("input") or {}).get("cycle_id"),
                            "district": (entry.get("input") or {}).get("district") or "ALL",
                            "started_at": created_at,
                        },
                    )
                elif agent == "ALERT" and status == "COMPLETED":
                    output = entry.get("output") or {}
                    await bus.publish(
                        "pipeline_complete",
                        {
                            "center_id": entry.get("center_id"),
                            "notifications_sent": output.get("notifications_sent"),
                            "completed_at": entry.get("completed_at") or created_at,
                        },
                    )
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            log.error(
                "sse_agent_log_poll_failed",
                error_type=type(exc).__name__,
                error=str(exc),
            )

        await asyncio.sleep(AGENT_LOG_POLL_SECONDS)


async def _heartbeat(bus: _EventBus) -> None:
    while True:
        await asyncio.sleep(HEARTBEAT_SECONDS)
        await bus.publish("heartbeat", {"ts": _utc_now_iso()})


@router.get("/stream")
async def stream(request: Request) -> EventSourceResponse:
    """Live pipeline feed. Auth: ?api_key=<AUSHADHI_API_KEY>."""
    loop = asyncio.get_running_loop()
    bus = _EventBus(loop)

    async def event_generator():
        watches: List[Any] = []
        tasks: List[asyncio.Task] = []
        try:
            watches = await asyncio.to_thread(_start_listeners, bus)
            tasks = [
                asyncio.create_task(_poll_agent_logs(bus), name="sse-agent-logs"),
                asyncio.create_task(_heartbeat(bus), name="sse-heartbeat"),
            ]

            yield {
                "event": "connected",
                "data": json.dumps(
                    {
                        "message": "AUSHADHI live stream connected",
                        "events": [
                            "sentinel_cycle_started",
                            "agent_step",
                            "inventory_updated",
                            "outbreak_detected",
                            "purchase_order_created",
                            "pipeline_complete",
                            "heartbeat",
                        ],
                        "connected_at": _utc_now_iso(),
                    }
                ),
            }

            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(bus.queue.get(), timeout=5.0)
                except asyncio.TimeoutError:
                    continue
                yield {"event": event["event"], "data": json.dumps(event["data"], default=str)}
        finally:
            for task in tasks:
                task.cancel()
            for watch in watches:
                try:
                    watch.unsubscribe()
                except Exception as exc:
                    log.warning("sse_watch_unsubscribe_failed", error=str(exc))
            log.info("sse_client_disconnected")

    log.info("sse_client_connected", client=request.client.host if request.client else None)
    return EventSourceResponse(event_generator())
