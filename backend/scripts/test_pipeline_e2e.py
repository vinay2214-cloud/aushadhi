#!/usr/bin/env python3
"""AUSHADHI — end-to-end pipeline test against real Firestore, Pub/Sub, Gemini.

Not pytest — just run it:
    cd backend && python3 scripts/test_pipeline_e2e.py

Starts all four Pub/Sub subscribers, calls sentinel_agent.scan_all_centers()
directly (not via Pub/Sub), then watches the chain run:

    SENTINEL -> DQMS -> FORECAST (+Gemini) -> PROCUREMENT -> ALERT

and verifies, against Firestore, that the cycle produced an OutbreakAlert and
a PurchaseOrder for PHC Razole.
"""

import asyncio
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from google.cloud.firestore_v1.base_query import FieldFilter  # noqa: E402

from agents.orchestrator import AushadhiOrchestrator  # noqa: E402
from config import settings  # noqa: E402

IDLE_SECONDS = 25.0
TIMEOUT_SECONDS = 900.0
RAZOLE = "phc_razole_001"

#: --recorded-gemini replays captured live responses instead of calling the
#: API, for when the free-tier daily quota is spent. Everything else in the
#: pipeline — Pub/Sub, Firestore, agent logic — still runs for real.
RECORDED_GEMINI = "--recorded-gemini" in sys.argv


def banner(text: str) -> None:
    print(f"\n{'=' * 78}\n  {text}\n{'=' * 78}", flush=True)


async def main() -> int:
    banner("AUSHADHI — END-TO-END PIPELINE TEST")
    print(f"  project : {settings.google_cloud_project}")
    print(f"  model   : {settings.gemini_model}")
    print(f"  topics  : {settings.pubsub_topic_prefix}-*")
    started_at = datetime.now(timezone.utc).isoformat()
    print(f"  started : {started_at}")

    orchestrator = AushadhiOrchestrator()
    if RECORDED_GEMINI:
        from scripts.recorded_gemini import RecordedGeminiService

        orchestrator.forecast_agent.gemini = RecordedGeminiService()
        print("  gemini  : RECORDED (replayed live responses — no API call)")
    else:
        print("  gemini  : LIVE")

    banner("STARTING SUBSCRIBERS (DQMS, FORECAST, PROCUREMENT, ALERT)")
    subscriber_task = asyncio.create_task(orchestrator.start_subscribers())
    await asyncio.sleep(2)

    banner("TRIGGERING SENTINEL CYCLE (direct call, not via Pub/Sub)")
    wall_start = time.monotonic()
    cycle = await orchestrator.run_sentinel_cycle()
    print(
        f"\n  cycle_id          : {cycle['cycle_id']}\n"
        f"  centers scanned   : {cycle['centers_scanned']}\n"
        f"  centers alerting  : {cycle['centers_alerting']}\n"
        f"  critical items    : {cycle['total_critical_items']}\n"
        f"  low items         : {cycle['total_low_items']}\n"
        f"  alerts / district : {cycle['alerts_per_district']}",
        flush=True,
    )

    banner("WATCHING PIPELINE — waiting for the chain to go quiet")
    went_idle = await orchestrator.wait_until_idle(
        idle_seconds=IDLE_SECONDS, timeout_seconds=TIMEOUT_SECONDS
    )
    elapsed = time.monotonic() - wall_start

    await orchestrator.stop()
    subscriber_task.cancel()
    try:
        await subscriber_task
    except asyncio.CancelledError:
        pass

    print(
        f"\n  pipeline idle     : {went_idle}\n"
        f"  messages handled  : {orchestrator.messages_handled}\n"
        f"  wall clock        : {elapsed:.1f}s",
        flush=True,
    )

    # ── VERIFY AGAINST FIRESTORE ────────────────────────────────────────
    banner("VERIFYING FIRESTORE STATE")
    db = orchestrator.firestore.db
    failures = 0

    def check(label: str, passed: bool, detail: str) -> None:
        nonlocal failures
        print(f"  {'PASS' if passed else 'FAIL'}  {label}: {detail}", flush=True)
        if not passed:
            failures += 1

    # 1. Outbreak alerts created during this run
    alerts = [
        snap.to_dict()
        async for snap in db.collection("outbreak_alerts")
        .where(filter=FieldFilter("created_at", ">=", started_at))
        .stream()
    ]
    print(f"\n[outbreak_alerts created this run: {len(alerts)}]")
    for alert in alerts:
        print(
            f"  - {alert['id']} | {alert['district']} | risk={alert['risk_level']} "
            f"| confidence={alert['confidence']} | {alert['disease_indicators']}"
        )
        print(f"      affected  : {alert['affected_center_ids']}")
        print(f"      cluster   : {alert['geographic_cluster']}")
        print(f"      summary   : {alert['outbreak_summary']}")
        for evidence in alert.get("key_evidence", []):
            print(
                f"      evidence  : {evidence['medicine']} "
                f"{evidence['current_daily_consumption']} vs "
                f"{evidence['normal_daily_consumption']} = {evidence['ratio']}x "
                f"[{evidence['significance']}]"
            )
        print(f"      linked POs: {alert.get('linked_po_ids', [])}")

    high_alerts = [a for a in alerts if a["risk_level"] in ("HIGH", "CRITICAL")]
    check(
        "OutbreakAlert with risk_level HIGH/CRITICAL",
        bool(high_alerts),
        f"{len(high_alerts)} of {len(alerts)} "
        + (f"({high_alerts[0]['risk_level']}, {high_alerts[0]['id']})" if high_alerts else ""),
    )
    check(
        "Razole inside the outbreak cluster",
        any(RAZOLE in a.get("affected_center_ids", []) for a in alerts),
        RAZOLE,
    )

    # 2. Purchase orders created during this run
    orders = [
        snap.to_dict()
        async for snap in db.collection("purchase_orders")
        .where(filter=FieldFilter("created_at", ">=", started_at))
        .stream()
    ]
    print(f"\n[purchase_orders created this run: {len(orders)}]")
    for po in sorted(orders, key=lambda p: p["po_number"]):
        print(
            f"  - {po['po_number']} | {po['health_center_name']} | {po['priority']} "
            f"| ₹{po['total_cost_inr']:,.2f} | {po['status']} "
            f"| outbreak_linked={po['outbreak_linked']}"
        )
        print(
            f"      warehouse : {po['warehouse_name']} "
            f"({po['warehouse_distance_km']} km, ETA {po['estimated_delivery_hours']}h)"
        )
        for line in po["line_items"]:
            print(
                f"      line      : {line['medicine_name']} x{line['requested_quantity']} "
                f"{line['unit']} @ ₹{line['unit_cost_inr']} = ₹{line['total_cost_inr']:,.2f} "
                f"[{line['urgency']}, stockout in {line['days_until_stockout']}d]"
            )

    razole_orders = [po for po in orders if po["health_center_id"] == RAZOLE]
    check(
        "PurchaseOrder created for PHC Razole",
        bool(razole_orders),
        razole_orders[0]["po_number"] if razole_orders else "none found",
    )
    check(
        "Razole PO is outbreak-linked",
        any(po["outbreak_linked"] for po in razole_orders),
        str([po.get("outbreak_alert_id") for po in razole_orders]),
    )

    # 3. Notifications
    notifications = [
        snap.to_dict()
        async for snap in db.collection("notifications")
        .where(filter=FieldFilter("created_at", ">=", started_at))
        .stream()
    ]
    by_type: dict = {}
    for note in notifications:
        by_type[note["type"]] = by_type.get(note["type"], 0) + 1
    print(f"\n[notifications created this run: {len(notifications)}] {by_type}")
    check("Stockout notifications sent", by_type.get("STOCKOUT_ALERT", 0) > 0, str(by_type))
    check("Outbreak notification sent", by_type.get("OUTBREAK_ALERT", 0) > 0, str(by_type))

    # 4. Agent logs — every agent should have run and completed
    logs = [
        snap.to_dict()
        async for snap in db.collection("agent_logs")
        .where(filter=FieldFilter("created_at", ">=", started_at))
        .stream()
    ]
    per_agent: dict = {}
    for entry in logs:
        key = (entry["agent_name"], entry["status"])
        per_agent[key] = per_agent.get(key, 0) + 1
    print(f"\n[agent_logs written this run: {len(logs)}]")
    for (agent, status), count in sorted(per_agent.items()):
        print(f"  - {agent:<12} {status:<10} {count}")
    for agent in ("SENTINEL", "DQMS", "FORECAST", "PROCUREMENT", "ALERT"):
        check(
            f"{agent} agent completed",
            per_agent.get((agent, "COMPLETED"), 0) > 0,
            f"{per_agent.get((agent, 'COMPLETED'), 0)} completed, "
            f"{per_agent.get((agent, 'FAILED'), 0)} failed",
        )

    # 5. The rendered outbreak notification, verbatim
    outbreak_notes = [n for n in notifications if n["type"] == "OUTBREAK_ALERT"]
    if outbreak_notes:
        banner("OUTBREAK NOTIFICATION AS DELIVERED")
        print(outbreak_notes[0]["body"])

    stockout_notes = [n for n in notifications if n["type"] == "STOCKOUT_ALERT"]
    razole_note = next(
        (n for n in stockout_notes if n.get("center_id") == RAZOLE), None
    )
    if razole_note:
        banner("STOCKOUT NOTIFICATION AS DELIVERED (PHC Razole)")
        print(razole_note["body"])

    banner(f"RESULT: {'ALL CHECKS PASSED' if failures == 0 else f'{failures} CHECK(S) FAILED'}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
