#!/usr/bin/env python3
"""AUSHADHI — FirestoreService smoke test against real Firestore.

Not pytest — just run it:
    cd backend && python3 scripts/test_firestore_service.py

Requires GOOGLE_APPLICATION_CREDENTIALS (or gcloud ADC) and
GOOGLE_CLOUD_PROJECT pointing at the project holding the seeded data.
"""

import asyncio
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from config import settings  # noqa: E402
from services.firestore_service import get_firestore_service  # noqa: E402


async def main() -> int:
    print("=" * 70)
    print("AUSHADHI — FirestoreService smoke test")
    print(f"  project : {settings.google_cloud_project}")
    print(f"  database: {settings.firestore_database_id}")
    print("=" * 70)

    svc = get_firestore_service()
    failures = 0

    # 1. Health centers
    print("\n[1] get_all_health_centers()")
    try:
        centers = await svc.get_all_health_centers()
        print(f"    -> {len(centers)} health centers")
        for c in centers:
            print(f"       - {c.id}: {c.name} ({c.type}, {c.district}) "
                  f"stock={c.status.overall_stock_status}")
    except Exception as exc:
        failures += 1
        print(f"    !! FAILED: {type(exc).__name__}: {str(exc)[:200]}")

    # 2. Critical inventory (collection group query)
    print("\n[2] get_inventory_by_urgency('CRITICAL')")
    try:
        critical = await svc.get_inventory_by_urgency("CRITICAL")
        print(f"    -> {len(critical)} CRITICAL items")
        for item in critical:
            print(f"       - {item.center_id} / {item.medicine_name}: "
                  f"{item.current_stock} units ({item.stock_percentage:.1f}%), "
                  f"stockout in {item.days_until_stockout}d")
        if not critical:
            print("       (none returned)")
    except Exception as exc:
        failures += 1
        print(f"    !! FAILED: {type(exc).__name__}: {str(exc)[:200]}")

    # 3. Medicines
    print("\n[3] get_all_medicines()")
    try:
        medicines = await svc.get_all_medicines()
        print(f"    -> {len(medicines)} medicines")
        for m in medicines:
            print(f"       - {m.id}: {m.name} [{m.category}] ₹{m.unit_cost_inr}")
    except Exception as exc:
        failures += 1
        print(f"    !! FAILED: {type(exc).__name__}: {str(exc)[:200]}")

    # 4. Warehouses
    print("\n[4] get_all_warehouses()")
    try:
        warehouses = await svc.get_all_warehouses()
        print(f"    -> {len(warehouses)} warehouses")
        for w in warehouses:
            print(f"       - {w.id}: {w.name} ({w.district}), "
                  f"{len(w.available_medicines)} medicines stocked")
    except Exception as exc:
        failures += 1
        print(f"    !! FAILED: {type(exc).__name__}: {str(exc)[:200]}")

    await svc.close()

    print("\n" + "=" * 70)
    print(f"RESULT: {'ALL CHECKS PASSED' if failures == 0 else f'{failures} CHECK(S) FAILED'}")
    print("=" * 70)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
