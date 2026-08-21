"""AUSHADHI — Agent 5: Alert + Report.

Trigger: subscribes to aushadhi-procured.
Gemini:  none — the three message templates in docs/AGENTS_SPEC.md Agent 5.

No SMS or email is sent in the demo: each notification is rendered from its
template, written to the `notifications` collection, and logged to stdout,
which Cloud Logging ingests. Swapping in a real transport later means
implementing _deliver() — everything upstream stays as it is.

Two notification types fire off a procurement message:
  STOCKOUT_ALERT  -> medical officer at the affected center, always
  OUTBREAK_ALERT  -> district health officer, only when the center is inside a
                     detected outbreak cluster, and only once per alert id
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

from utils.logger import get_logger

from agents.base_agent import BaseAgent

log = get_logger(__name__)

DASHBOARD_URL = "https://aushadhi.example.gov.in/dashboard"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class AlertReportAgent(BaseAgent):
    """Renders and records the notifications a procurement run should produce."""

    name = "ALERT"
    action = "send_notifications"
    publishes_to = None
    subscribes_to = "procured-sub"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        # One outbreak alert should reach the district officer once, not once
        # per center in the cluster.
        self._outbreak_notified: Set[str] = set()

    async def process(
        self, center_id: Optional[str], payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        center_id = center_id or payload.get("center_id")
        po = payload.get("purchase_order") or {}
        outbreak = payload.get("outbreak") or {}

        sent: List[Dict[str, Any]] = []

        stockout_body = self._render_stockout_alert(payload, po)
        sent.append(
            await self._deliver(
                notification_type="STOCKOUT_ALERT",
                recipient=payload.get("medical_officer") or "Medical Officer",
                recipient_email=payload.get("contact_email"),
                subject=(
                    f"AUSHADHI Alert — {payload.get('center_name')} | "
                    f"{payload.get('district')}"
                ),
                body=stockout_body,
                center_id=center_id,
                payload=payload,
            )
        )

        alert_id = outbreak.get("outbreak_alert_id")
        if alert_id and outbreak.get("center_affected") and alert_id not in self._outbreak_notified:
            self._outbreak_notified.add(alert_id)
            sent.append(
                await self._deliver(
                    notification_type="OUTBREAK_ALERT",
                    recipient=f"District Health Officer — {payload.get('district')}",
                    recipient_email=None,
                    subject=(
                        f"AUSHADHI OUTBREAK INTELLIGENCE ALERT — {payload.get('district')} "
                        f"| {outbreak.get('risk_level')}"
                    ),
                    body=self._render_outbreak_alert(payload, po, outbreak),
                    center_id=center_id,
                    payload=payload,
                    outbreak_alert_id=alert_id,
                )
            )

        return {
            "center_id": center_id,
            "notifications_sent": len(sent),
            "types": [n["type"] for n in sent],
            "notification_ids": [n["id"] for n in sent],
        }

    # ────────────────────────────── delivery ───────────────────────────

    async def _deliver(
        self,
        notification_type: str,
        recipient: str,
        recipient_email: Optional[str],
        subject: str,
        body: str,
        center_id: Optional[str],
        payload: Dict[str, Any],
        outbreak_alert_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Record + log a notification. Demo transport: Cloud Logging only."""
        record = {
            "type": notification_type,
            "channel": "CLOUD_LOGGING",
            "status": "SENT",
            "recipient": recipient,
            "recipient_email": recipient_email,
            "subject": subject,
            "body": body,
            "center_id": center_id,
            "center_name": payload.get("center_name"),
            "district": payload.get("district"),
            "cycle_id": payload.get("cycle_id"),
            "po_id": (payload.get("purchase_order") or {}).get("po_id"),
            "po_number": (payload.get("purchase_order") or {}).get("po_number"),
            "outbreak_alert_id": outbreak_alert_id,
            "sent_at": _utc_now_iso(),
        }
        notification_id = await self.firestore.create_notification(record)

        self.log.info(
            "notification_sent",
            notification_id=notification_id,
            notification_type=notification_type,
            recipient=recipient,
            center_id=center_id,
            po_number=record["po_number"],
            outbreak_alert_id=outbreak_alert_id,
        )
        # The rendered message itself, so it shows up verbatim in Cloud Logging.
        self.log.info("notification_body", notification_type=notification_type, body=body)

        return {"id": notification_id, "type": notification_type, "recipient": recipient}

    # ───────────────────────────── templates ───────────────────────────

    def _render_stockout_alert(self, payload: Dict[str, Any], po: Dict[str, Any]) -> str:
        lines = []
        for item in po.get("line_items", []):
            days = item.get("days_until_stockout")
            supply = f"{days} days supply" if days else "supply exhausted"
            lines.append(
                f"• {item['medicine_name']}: {item['requested_quantity']} units ordered "
                f"({supply} at current rate) — {item['urgency']}"
            )

        warehouse = po.get("warehouse", {})
        return f"""AUSHADHI Alert — {payload.get('center_name')} | {payload.get('district')}

⚠ CRITICAL STOCKOUT WARNING ⚠

The following medicines are at CRITICAL levels (< 15% stock):
{chr(10).join(lines) if lines else '• (no line items)'}

AUTOMATED ACTION TAKEN:
Purchase Order {po.get('po_number')} generated
Nearest warehouse: {warehouse.get('name')} ({warehouse.get('distance_km')} km)
Estimated delivery: Within {po.get('estimated_delivery_hours')} hours of approval

ACTION REQUIRED FROM YOU:
Please approve PO {po.get('po_number')} at {DASHBOARD_URL}/purchase-orders/{po.get('po_id')}

AUSHADHI System | {payload.get('district')} District Health Programme"""

    def _render_outbreak_alert(
        self, payload: Dict[str, Any], po: Dict[str, Any], outbreak: Dict[str, Any]
    ) -> str:
        confidence = outbreak.get("confidence") or 0.0
        indicators = " / ".join(outbreak.get("disease_indicators", [])) or "UNSPECIFIED"
        evidence = ", ".join(
            f"{e.get('medicine')} {e.get('ratio')}x baseline"
            for e in outbreak.get("key_evidence", [])[:4]
        )
        actions = "\n".join(
            f"{i}. {action}"
            for i, action in enumerate(outbreak.get("recommended_actions", []), start=1)
        )
        surveillance = "\n".join(
            f"• {step}" for step in outbreak.get("recommended_surveillance_actions", [])
        )
        affected = outbreak.get("affected_center_ids", [])

        return f"""AUSHADHI OUTBREAK INTELLIGENCE ALERT
District: {payload.get('district')} | Priority: {outbreak.get('risk_level')} | Confidence: {confidence * 100:.0f}%

DETECTED PATTERN: {indicators}

Affected areas: {outbreak.get('geographic_cluster')} ({len(affected)} facilities)
Affected facilities: {', '.join(affected) if affected else 'n/a'}
Evidence: {evidence or 'see full analysis'}

SUMMARY:
{outbreak.get('outbreak_summary')}

IMMEDIATE RECOMMENDED ACTIONS:
{actions or '1. Review the full analysis on the dashboard'}

SURVEILLANCE:
{surveillance or '• Await district response team assessment'}

Emergency procurement already initiated: PO {po.get('po_number')} ({po.get('priority')}) —
{po.get('warehouse', {}).get('name')}, ETA {po.get('estimated_delivery_hours')}h after approval.

This alert was generated by AUSHADHI before any patient was officially reported.

For full analysis: {DASHBOARD_URL}/outbreaks/{outbreak.get('outbreak_alert_id')}"""
