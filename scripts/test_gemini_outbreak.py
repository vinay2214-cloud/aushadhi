#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║          AUSHADHI — GEMINI OUTBREAK DETECTION VALIDATION TEST               ║
║          (google-genai SDK + gemini-3.5-flash + retry logic)                ║
╚══════════════════════════════════════════════════════════════════════════════╝

Usage:
    echo "GOOGLE_API_KEY=your-key" > .env
    python3 scripts/test_gemini_outbreak.py

Install deps (one time):
    pip3 install google-genai python-dotenv
"""

import os
import sys
import json
import time

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
BLUE   = "\033[94m"
PURPLE = "\033[95m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

def ok(msg):   print(f"  {GREEN}✅ {msg}{RESET}")
def fail(msg): print(f"  {RED}❌ {msg}{RESET}")
def warn(msg): print(f"  {YELLOW}⚠️  {msg}{RESET}")
def info(msg): print(f"  {BLUE}ℹ️  {msg}{RESET}")
def section(title):
    print(f"\n{BOLD}{CYAN}{'─' * 60}{RESET}")
    print(f"{BOLD}{CYAN}  {title}{RESET}")
    print(f"{BOLD}{CYAN}{'─' * 60}{RESET}")

MODEL_NAME = "gemini-3.5-flash"
# gemini-3.5-flash is served from Vertex's "global" endpoint only; regional
# endpoints such as us-central1 return 404 NOT_FOUND for this model.
VERTEX_LOCATION = os.environ.get("VERTEX_LOCATION", "global")
MAX_RETRIES = 4
RETRY_DELAY_SECONDS = 8   # 503 = server overload, needs real wait time

OUTBREAK_SYSTEM_PROMPT = """You are AUSHADHI's epidemiological surveillance intelligence for Andhra Pradesh, India.

Your role is to detect emerging disease outbreaks by analyzing medicine consumption patterns across multiple health centers. You operate on a key insight: disease outbreaks create distinctive "consumption signatures" in the medicines used to treat them, BEFORE official patient data or disease reports are filed.

You are trained on these outbreak signatures for India:

CHOLERA / SEVERE DIARRHEA:
  Primary: ORS packets (+200% baseline), Zinc tablets (+180% baseline), IV Fluids (+250% baseline)
  Supporting: Metronidazole (+150%), Cotrimoxazole (+120%)
  Geographic pattern: Clustered (3+ adjacent centers affected)
  Seasonal: Peaks post-flood events, monsoon, near water bodies

MALARIA:
  Primary: Chloroquine (+150% baseline), Artesunate/ACT (+200% baseline), Paracetamol (+150%)
  Supporting: Primaquine (+120%), RDT kits depleting
  Geographic pattern: Can be widespread or focal (stagnant water sources)
  Seasonal: August-October (post-monsoon) in AP

INFLUENZA / ILI (Influenza-Like Illness):
  Primary: Paracetamol (+200% baseline), Antihistamines (+150%), Oseltamivir if available
  Supporting: Amoxicillin (+130%), Azithromycin (+120%)
  Geographic pattern: Widespread simultaneously (multiple centers, large geographic spread)
  Seasonal: Post-monsoon (Oct-Nov), winter (Jan-Feb)

GASTROENTERITIS (Non-cholera):
  Primary: Metronidazole (+180% baseline), ORS (+150% baseline)
  Supporting: Antispasmodics (+130%), Domperidone (+120%)
  Geographic pattern: Localized to 1-3 centers
  Seasonal: Year-round, peaks summer

DENGUE:
  Primary: Paracetamol (+200%), NO antibiotic increase (key differential)
  Supporting: IV Fluids (+200%), Platelet transfusion requests
  Geographic pattern: Focal to urban/semi-urban clusters
  Seasonal: August-November in AP

CRITICAL RULES:
- Missing an outbreak is far worse than a false positive. When uncertain, flag at MEDIUM.
- A single center showing anomalies is suspicious but not sufficient for HIGH/CRITICAL.
- 3+ centers in geographic proximity with matching consumption signatures = HIGH risk.
- 5+ centers = CRITICAL. Alert immediately.
- Consumption ratio > 3x baseline for a primary indicator = strong evidence.
- Combination of 2+ primary indicators simultaneously = high confidence.

Return ONLY valid JSON. No markdown, no preamble, no explanation outside the JSON."""


RAZOLE_OUTBREAK_PROMPT = """District: East Godavari, Andhra Pradesh
Date: 2026-08-20
Season: Monsoon (August) | Recent weather: Heavy rainfall, flooding reported in low-lying areas near Krishna-Godavari delta

CONSUMPTION ANOMALIES DETECTED THIS CYCLE:

PHC Razole (PHC, Razole mandal):
  - ORS Packets: 46 units today (7d avg baseline: 12, ratio: 3.8x, anomaly: True)
  - Zinc Tablets 20mg: 29 units today (7d avg baseline: 8, ratio: 3.6x, anomaly: True)
  - IV Normal Saline 500ml: 11 units today (7d avg baseline: 3, ratio: 3.7x, anomaly: True)
  - Metronidazole 400mg: 18 units today (7d avg baseline: 9, ratio: 2.0x, anomaly: False)
  - Paracetamol 500mg: 42 units today (7d avg baseline: 35, ratio: 1.2x, anomaly: False)

PHC Amalapuram (PHC, Amalapuram mandal):
  - ORS Packets: 38 units today (7d avg baseline: 10, ratio: 3.8x, anomaly: True)
  - Zinc Tablets 20mg: 24 units today (7d avg baseline: 7, ratio: 3.4x, anomaly: True)
  - IV Normal Saline 500ml: 9 units today (7d avg baseline: 2, ratio: 4.5x, anomaly: True)
  - Metronidazole 400mg: 14 units today (7d avg baseline: 8, ratio: 1.75x, anomaly: False)

CHC Razole Community (CHC, Razole mandal — 6km from PHC Razole):
  - ORS Packets: 31 units today (7d avg baseline: 9, ratio: 3.4x, anomaly: True)
  - Zinc Tablets 20mg: 19 units today (7d avg baseline: 6, ratio: 3.2x, anomaly: True)
  - IV Normal Saline 500ml: 7 units today (7d avg baseline: 2, ratio: 3.5x, anomaly: True)

PHC Mandapeta (PHC, Mandapeta mandal):
  - Paracetamol 500mg: 58 units today (7d avg baseline: 45, ratio: 1.3x, anomaly: False)
  - Amoxicillin 500mg: 22 units today (7d avg baseline: 18, ratio: 1.2x, anomaly: False)
  - ORS Packets: 15 units today (7d avg baseline: 11, ratio: 1.4x, anomaly: False)

CHC Rajahmundry Urban (CHC, Rajahmundry):
  - All medicines within normal range (ratio 0.9x-1.2x)
  - No anomalies detected

Total centers reporting anomalies: 3
Total centers monitored: 5

Analyze these consumption patterns for disease outbreak signals.
Return exactly this JSON structure:
{
  "outbreak_detected": <boolean>,
  "risk_level": "<CRITICAL|HIGH|MEDIUM|LOW|NONE>",
  "disease_indicators": ["<CHOLERA|MALARIA|INFLUENZA|GASTROENTERITIS|DENGUE|OTHER>"],
  "affected_centers": ["<center_id_1>", "<center_id_2>"],
  "geographic_cluster": "<description of affected area>",
  "key_evidence": [
    {
      "medicine": "<medicine_name>",
      "normal_daily_consumption": <number>,
      "current_daily_consumption": <number>,
      "ratio": <float>,
      "significance": "<HIGH|MEDIUM|LOW>"
    }
  ],
  "confidence": <float 0.0-1.0>,
  "recommended_actions": [
    "<specific action 1>",
    "<specific action 2>"
  ],
  "outbreak_summary": "<one clear sentence for the district health officer>",
  "differential_diagnosis": "<other possible explanations>",
  "recommended_surveillance_actions": ["<specific surveillance step>"]
}"""

FORECAST_SYSTEM_PROMPT = """You are AUSHADHI's demand forecasting intelligence for rural healthcare supply chains in India.

Your job is to analyze medicine consumption data from a health center and predict future demand accurately.

You understand Indian seasonal disease patterns:
- Monsoon (June-September): Malaria, Diarrhea, Cholera, Leptospirosis
- Winter (November-February): Respiratory infections, Influenza
- Summer (March-May): Heat stroke, Gastroenteritis, Typhoid
- Year-round: OPD visits, maternal health, routine medications

Return ONLY a valid JSON object. No markdown, no explanation, no preamble."""

FORECAST_PROMPT = """Health Center: PHC Razole (PHC) — East Godavari District, Andhra Pradesh
Medicine: ORS Packets (WHO Formula) (ORS_ELECTROLYTE)
Current Stock: 45 units
Minimum Threshold: 200 units
Maximum Capacity: 600 units
Current Month: August (Monsoon peak)
Catchment Population: 28,000

Consumption History (last 14 days):
  2026-08-07: consumed 12 units, opening stock 580
  2026-08-08: consumed 11 units, opening stock 568
  2026-08-09: consumed 13 units, opening stock 557
  2026-08-10: consumed 12 units, opening stock 544
  2026-08-11: consumed 14 units, opening stock 532
  2026-08-12: consumed 15 units, opening stock 518
  2026-08-13: consumed 18 units, opening stock 503
  2026-08-14: consumed 22 units, opening stock 485
  2026-08-15: consumed 28 units, opening stock 463
  2026-08-16: consumed 33 units, opening stock 435
  2026-08-17: consumed 38 units, opening stock 402
  2026-08-18: consumed 41 units, opening stock 364
  2026-08-19: consumed 44 units, opening stock 323
  2026-08-20: consumed 46 units, opening stock 277

7-day average daily consumption: 30.5 units
30-day average daily consumption: 18.2 units
Trend: SHARPLY_INCREASING (+280.0% vs previous period)
Anomaly flag: True (ratio: 3.8x)

Predict demand and reorder requirements. Return exactly this JSON structure:
{
  "predicted_daily_consumption_next_7_days": <number>,
  "predicted_daily_consumption_next_30_days": <number>,
  "days_until_stockout_at_current_trend": <integer>,
  "reorder_urgency": "<CRITICAL|HIGH|MEDIUM|LOW>",
  "recommended_order_quantity": <integer>,
  "forecast_confidence": <float 0.0-1.0>,
  "seasonal_adjustment": "<increase|decrease|stable>",
  "seasonal_reasoning": "<one sentence>",
  "forecasting_reasoning": "<one sentence explaining the prediction>"
}"""


def call_with_retry(client, types, model, contents, system_instruction, max_tokens):
    """Call Gemini with retry on 503/transient errors.

    IMPORTANT: gemini-3.5-flash has "thinking" enabled by default (medium level),
    and thinking tokens are deducted from the SAME max_output_tokens budget as the
    actual answer. Without capping thinking_level, the model can burn its entire
    token budget reasoning internally and return an empty/truncated response
    (finish_reason=MAX_TOKENS) even with generous limits like 2048.
    Fix: set thinking_level="low" to reserve most of the budget for real output,
    and use a generous max_output_tokens ceiling as a safety margin.
    """
    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = client.models.generate_content(
                model=model,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    max_output_tokens=max_tokens,
                    response_mime_type="application/json",
                    thinking_config=types.ThinkingConfig(thinking_level="low"),
                ),
            )
            return response
        except Exception as e:
            last_error = e
            err_str = str(e)
            is_retryable = "503" in err_str or "UNAVAILABLE" in err_str or "429" in err_str
            if is_retryable and attempt < MAX_RETRIES:
                warn(f"Attempt {attempt}/{MAX_RETRIES} failed ({type(e).__name__}). "
                     f"Retrying in {RETRY_DELAY_SECONDS}s (server overload, not your code)...")
                time.sleep(RETRY_DELAY_SECONDS)
            else:
                raise last_error
    raise last_error


def run_test() -> bool:
    from google import genai
    from google.genai import types

    # Vertex AI, not AI Studio: the AI Studio key caps at 20 requests/day on the
    # free tier regardless of billing. Vertex bills the GCP project directly and
    # authenticates with Application Default Credentials — no key involved.
    client = genai.Client(
        vertexai=True,
        project=os.environ.get("GOOGLE_CLOUD_PROJECT", "aushadhi-hackathon-2026"),
        location=VERTEX_LOCATION,
    )
    all_passed = True

    # ── TEST 1: OUTBREAK DETECTION ──────────────────────────────────────────
    section("TEST 1: Outbreak Detection (The Twist — Most Critical)")
    print(f"  Model: {MODEL_NAME}")
    print(f"  Scenario: Razole + Amalapuram cholera consumption signature")
    print(f"  Calling Gemini API (with auto-retry on server overload)...")

    try:
        start = time.time()
        response = call_with_retry(
            client, types, MODEL_NAME, RAZOLE_OUTBREAK_PROMPT,
            OUTBREAK_SYSTEM_PROMPT, max_tokens=8192
        )
        elapsed = time.time() - start
        print(f"  Response received in {elapsed:.1f}s\n")

        try:
            # Gemini occasionally appends stray trailing characters after
            # valid JSON (e.g., an extra "}"). Parse only the first complete
            # JSON object and ignore anything after it, rather than failing.
            decoder = json.JSONDecoder()
            result, _end_index = decoder.raw_decode(response.text.strip())
        except json.JSONDecodeError as e:
            fail(f"JSON PARSE ERROR: {e}")
            print(f"\n  {YELLOW}Raw response (to diagnose):{RESET}\n{response.text}")
            print(f"\n  {YELLOW}finish_reason: {response.candidates[0].finish_reason if response.candidates else 'unknown'}{RESET}")
            all_passed = False
            result = None

        if result:
            print(f"{PURPLE}  Full Gemini Response:{RESET}")
            print(f"{PURPLE}{json.dumps(result, indent=4)}{RESET}\n")

            t1_pass = True

            v = result.get("outbreak_detected")
            if v is True:
                ok(f"outbreak_detected = {v}")
            else:
                fail(f"outbreak_detected = {v}  (expected: true)")
                t1_pass = False

            v = result.get("risk_level")
            if v in ["HIGH", "CRITICAL"]:
                ok(f"risk_level = {v}")
            else:
                fail(f"risk_level = {v}  (expected: HIGH or CRITICAL)")
                t1_pass = False

            v = result.get("disease_indicators", [])
            if "CHOLERA" in v:
                ok(f"disease_indicators = {v}  ← CHOLERA detected")
            else:
                fail(f"disease_indicators = {v}  (expected: CHOLERA in list)")
                t1_pass = False

            v = result.get("confidence", 0)
            if v > 0.70:
                ok(f"confidence = {v:.2f}  (> 0.70 threshold)")
            else:
                fail(f"confidence = {v:.2f}  (expected: > 0.70)")
                t1_pass = False

            affected = result.get("affected_centers", [])
            if len(affected) >= 3:
                ok(f"affected_centers = {affected}  (3+ centers confirms HIGH-risk cluster threshold)")
            elif any("razole" in c.lower() or "amalapuram" in c.lower() for c in affected):
                ok(f"affected_centers = {affected}")
            else:
                fail(f"affected_centers = {affected}  (expected: Razole + Amalapuram + Razole CHC)")
                t1_pass = False

            evidence = result.get("key_evidence", [])
            high_evidence = [e for e in evidence if e.get("ratio", 0) > 2.0]
            if len(high_evidence) >= 2:
                ok(f"key_evidence: {len(high_evidence)} items with ratio > 2.0")
                for e in high_evidence:
                    print(f"      {e['medicine']}: {e['ratio']}x  [{e['significance']}]")
            else:
                fail(f"key_evidence: only {len(high_evidence)} items with ratio > 2.0")
                t1_pass = False

            actions = result.get("recommended_actions", [])
            if len(actions) >= 2:
                ok(f"recommended_actions: {len(actions)} actions generated")
            else:
                fail(f"recommended_actions: only {len(actions)} (expected >= 2)")
                t1_pass = False

            summary = result.get("outbreak_summary", "")
            if summary:
                ok(f"outbreak_summary: \"{summary[:80]}...\"")
            else:
                fail("outbreak_summary: empty")
                t1_pass = False

            if t1_pass:
                print(f"\n{GREEN}{BOLD}  TEST 1 PASSED ✅ — Outbreak detection working correctly{RESET}")
            else:
                print(f"\n{RED}{BOLD}  TEST 1 FAILED ❌{RESET}")
                all_passed = False

    except Exception as e:
        fail(f"API call failed after {MAX_RETRIES} attempts: {type(e).__name__}: {e}")
        all_passed = False

    # ── TEST 2: DEMAND FORECASTING ───────────────────────────────────────────
    section("TEST 2: Demand Forecasting (Critical for Procurement)")
    print(f"  Scenario: PHC Razole ORS stockout prediction")
    print(f"  Calling Gemini API (with auto-retry on server overload)...")

    try:
        start = time.time()
        response2 = call_with_retry(
            client, types, MODEL_NAME, FORECAST_PROMPT,
            FORECAST_SYSTEM_PROMPT, max_tokens=4096
        )
        elapsed = time.time() - start
        print(f"  Response received in {elapsed:.1f}s\n")

        try:
            result2 = json.loads(response2.text)
        except json.JSONDecodeError as e:
            fail(f"JSON PARSE ERROR: {e}")
            print(f"\n  {YELLOW}Raw response (to diagnose):{RESET}\n{response2.text}")
            print(f"\n  {YELLOW}finish_reason: {response2.candidates[0].finish_reason if response2.candidates else 'unknown'}{RESET}")
            return False

        print(f"{PURPLE}  Full Gemini Response:{RESET}")
        print(f"{PURPLE}{json.dumps(result2, indent=4)}{RESET}\n")

        t2_pass = True

        v = result2.get("days_until_stockout_at_current_trend", 999)
        if v <= 3:
            ok(f"days_until_stockout = {v}  (correctly urgent)")
        elif v <= 7:
            warn(f"days_until_stockout = {v}  (acceptable, but should be ≤3)")
        else:
            fail(f"days_until_stockout = {v}  (incorrect — should be 1-2 days)")
            t2_pass = False

        v = result2.get("reorder_urgency", "")
        if v == "CRITICAL":
            ok(f"reorder_urgency = {v}")
        elif v == "HIGH":
            warn(f"reorder_urgency = {v}  (acceptable but CRITICAL expected)")
        else:
            fail(f"reorder_urgency = {v}  (expected: CRITICAL)")
            t2_pass = False

        v = result2.get("recommended_order_quantity", 0)
        if v >= 300:
            ok(f"recommended_order_quantity = {v} units")
        else:
            fail(f"recommended_order_quantity = {v}  (too low, expected >= 300)")
            t2_pass = False

        v = result2.get("forecast_confidence", 0)
        if v >= 0.70:
            ok(f"forecast_confidence = {v:.2f}")
        else:
            warn(f"forecast_confidence = {v:.2f}  (low but acceptable)")

        v = result2.get("seasonal_adjustment", "")
        if v == "increase":
            ok(f"seasonal_adjustment = {v}  (correct for monsoon)")
        else:
            warn(f"seasonal_adjustment = {v}  (expected: increase for August monsoon)")

        reasoning = result2.get("forecasting_reasoning", "")
        if reasoning:
            ok(f"forecasting_reasoning: \"{reasoning[:80]}...\"")
        else:
            fail("forecasting_reasoning: empty")
            t2_pass = False

        if t2_pass:
            print(f"\n{GREEN}{BOLD}  TEST 2 PASSED ✅ — Demand forecasting working correctly{RESET}")
        else:
            print(f"\n{RED}{BOLD}  TEST 2 FAILED ❌{RESET}")
            all_passed = False

    except Exception as e:
        fail(f"API call failed after {MAX_RETRIES} attempts: {type(e).__name__}: {e}")
        all_passed = False

    # ── FINAL VERDICT ────────────────────────────────────────────────────────
    section("FINAL VERDICT")
    if all_passed:
        print(f"""
{GREEN}{BOLD}  ██████████████████████████████████████████████
  ██                                          ██
  ██    BOTH TESTS PASSED — BUILD AUSHADHI   ██
  ██                                          ██
  ██████████████████████████████████████████████{RESET}

  {GREEN}Your Gemini integration is working correctly on gemini-3.5-flash.{RESET}
  {GREEN}Proceed to build agents/forecast_agent.py with full confidence.{RESET}
""")
    else:
        print(f"""
{RED}{BOLD}  ████████████████████████████████████████████
  ██    ONE OR MORE TESTS FAILED           ██
  ██    DO NOT BUILD BACKEND YET           ██
  ████████████████████████████████████████████{RESET}

  {YELLOW}If you saw 503/UNAVAILABLE errors even after retries:{RESET}
  Google's servers are overloaded right now. Wait 2-3 minutes and run the
  script again — this is not a bug in your code.

  {YELLOW}If you saw a JSON parse error with finish_reason=MAX_TOKENS:{RESET}
  gemini-3.5-flash "thinks" before answering, and that reasoning shares the
  same token budget as your output. This script already sets
  thinking_level="low" and generous max_output_tokens (8192/4096) to fix
  this — if it still happens, try thinking_level="minimal" instead.

  {YELLOW}If confidence or classifications are wrong:{RESET}
  Re-run once — Gemini output can vary slightly between calls even at
  low temperature. If it fails consistently, the prompt may need tuning.
""")

    return all_passed


if __name__ == "__main__":
    print(f"""
{BOLD}{GREEN}
╔══════════════════════════════════════════════════════════════════════════════╗
║              AUSHADHI — GEMINI VALIDATION TEST (google-genai)               ║
║              East Godavari Cholera Outbreak Scenario                        ║
╚══════════════════════════════════════════════════════════════════════════════╝
{RESET}""")

    try:
        from google import genai  # noqa: F401
    except ImportError:
        fail("google-genai not installed")
        print(f"\n  Run: {YELLOW}pip3 uninstall -y google-generativeai && pip3 install google-genai{RESET}")
        sys.exit(1)

    project = os.environ.get("GOOGLE_CLOUD_PROJECT", "aushadhi-hackathon-2026")

    info(f"Auth: Vertex AI via Application Default Credentials (no API key)")
    info(f"Project: {project} | Location: {VERTEX_LOCATION}")
    info(f"Model: {MODEL_NAME}")
    info(f"Retry policy: up to {MAX_RETRIES} attempts, {RETRY_DELAY_SECONDS}s apart on server overload")
    info("Running 2 tests (outbreak detection + demand forecast)\n")

    success = run_test()
    sys.exit(0 if success else 1)
