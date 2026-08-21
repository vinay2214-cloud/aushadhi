#!/usr/bin/env python3
"""AUSHADHI — GeminiService smoke test against the live Gemini API.

Not pytest — just run it:
    cd backend && python3 scripts/test_gemini_service.py

Replays the Razole + Amalapuram + CHC Razole cholera scenario from
scripts/test_gemini_outbreak.py through GeminiService.detect_outbreak() and
asserts the validated expectations: risk_level HIGH/CRITICAL, CHOLERA in
disease_indicators, confidence > 0.70.
"""

import asyncio
import json
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from config import settings  # noqa: E402
from services.gemini_service import (  # noqa: E402
    build_outbreak_prompt,
    get_gemini_service,
)

DISTRICT = "East Godavari"
DATE = "2026-08-20"

# Same scenario as scripts/test_gemini_outbreak.py, expressed as the
# centers_data structure build_outbreak_prompt() consumes.
CENTERS_DATA = [
    {
        "center_id": "phc_razole_001",
        "name": "PHC Razole",
        "type": "PHC",
        "subdistrict": "Razole mandal",
        "has_anomaly": True,
        "medicines": [
            {"name": "ORS Packets", "current_consumption": 46,
             "baseline_consumption": 12, "consumption_ratio": 3.8, "anomaly_flag": True},
            {"name": "Zinc Tablets 20mg", "current_consumption": 29,
             "baseline_consumption": 8, "consumption_ratio": 3.6, "anomaly_flag": True},
            {"name": "IV Normal Saline 500ml", "current_consumption": 11,
             "baseline_consumption": 3, "consumption_ratio": 3.7, "anomaly_flag": True},
            {"name": "Metronidazole 400mg", "current_consumption": 18,
             "baseline_consumption": 9, "consumption_ratio": 2.0, "anomaly_flag": False},
            {"name": "Paracetamol 500mg", "current_consumption": 42,
             "baseline_consumption": 35, "consumption_ratio": 1.2, "anomaly_flag": False},
        ],
    },
    {
        "center_id": "phc_amalapuram_002",
        "name": "PHC Amalapuram",
        "type": "PHC",
        "subdistrict": "Amalapuram mandal",
        "has_anomaly": True,
        "medicines": [
            {"name": "ORS Packets", "current_consumption": 38,
             "baseline_consumption": 10, "consumption_ratio": 3.8, "anomaly_flag": True},
            {"name": "Zinc Tablets 20mg", "current_consumption": 24,
             "baseline_consumption": 7, "consumption_ratio": 3.4, "anomaly_flag": True},
            {"name": "IV Normal Saline 500ml", "current_consumption": 9,
             "baseline_consumption": 2, "consumption_ratio": 4.5, "anomaly_flag": True},
            {"name": "Metronidazole 400mg", "current_consumption": 14,
             "baseline_consumption": 8, "consumption_ratio": 1.75, "anomaly_flag": False},
        ],
    },
    {
        "center_id": "chc_razole_003",
        "name": "CHC Razole Community",
        "type": "CHC",
        "subdistrict": "Razole mandal — 6km from PHC Razole",
        "has_anomaly": True,
        "medicines": [
            {"name": "ORS Packets", "current_consumption": 31,
             "baseline_consumption": 9, "consumption_ratio": 3.4, "anomaly_flag": True},
            {"name": "Zinc Tablets 20mg", "current_consumption": 19,
             "baseline_consumption": 6, "consumption_ratio": 3.2, "anomaly_flag": True},
            {"name": "IV Normal Saline 500ml", "current_consumption": 7,
             "baseline_consumption": 2, "consumption_ratio": 3.5, "anomaly_flag": True},
        ],
    },
    {
        "center_id": "phc_mandapeta_004",
        "name": "PHC Mandapeta",
        "type": "PHC",
        "subdistrict": "Mandapeta mandal",
        "has_anomaly": False,
        "medicines": [
            {"name": "Paracetamol 500mg", "current_consumption": 58,
             "baseline_consumption": 45, "consumption_ratio": 1.3, "anomaly_flag": False},
            {"name": "Amoxicillin 500mg", "current_consumption": 22,
             "baseline_consumption": 18, "consumption_ratio": 1.2, "anomaly_flag": False},
            {"name": "ORS Packets", "current_consumption": 15,
             "baseline_consumption": 11, "consumption_ratio": 1.4, "anomaly_flag": False},
        ],
    },
    {
        "center_id": "chc_rajahmundry_005",
        "name": "CHC Rajahmundry Urban",
        "type": "CHC",
        "subdistrict": "Rajahmundry",
        "has_anomaly": False,
        "medicines": [
            {"name": "Paracetamol 500mg", "current_consumption": 40,
             "baseline_consumption": 38, "consumption_ratio": 1.05, "anomaly_flag": False},
            {"name": "ORS Packets", "current_consumption": 10,
             "baseline_consumption": 11, "consumption_ratio": 0.9, "anomaly_flag": False},
        ],
    },
]


async def main() -> int:
    print("=" * 70)
    print("AUSHADHI — GeminiService smoke test (detect_outbreak)")
    print(f"  model   : {settings.gemini_model}")
    print(f"  thinking: {settings.gemini_thinking_level}")
    print("=" * 70)

    print("\n--- PROMPT SENT TO GEMINI " + "-" * 44)
    print(build_outbreak_prompt(DISTRICT, CENTERS_DATA, DATE))
    print("-" * 70)

    svc = get_gemini_service()
    result = await svc.detect_outbreak(CENTERS_DATA, DISTRICT, DATE)

    print("\n--- GEMINI RESPONSE " + "-" * 50)
    print(json.dumps(result, indent=2))
    print("-" * 70)

    failures = 0

    def check(label, passed, actual):
        nonlocal failures
        print(f"  {'PASS' if passed else 'FAIL'}  {label}: {actual}")
        if not passed:
            failures += 1

    print("\n--- ASSERTIONS " + "-" * 55)
    check("outbreak_detected is true", result.get("outbreak_detected") is True,
          result.get("outbreak_detected"))
    check("risk_level in (HIGH, CRITICAL)", result.get("risk_level") in ("HIGH", "CRITICAL"),
          result.get("risk_level"))
    check("CHOLERA in disease_indicators", "CHOLERA" in result.get("disease_indicators", []),
          result.get("disease_indicators"))
    conf = result.get("confidence", 0)
    check("confidence > 0.70", isinstance(conf, (int, float)) and conf > 0.70, conf)
    affected = result.get("affected_centers", [])
    check("3+ affected centers", len(affected) >= 3, affected)
    evidence = [e for e in result.get("key_evidence", []) if e.get("ratio", 0) > 2.0]
    check("2+ key_evidence items with ratio > 2.0", len(evidence) >= 2, len(evidence))

    print("\n" + "=" * 70)
    print("RESULT:", "ALL CHECKS PASSED" if failures == 0 else f"{failures} CHECK(S) FAILED")
    print("=" * 70)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
