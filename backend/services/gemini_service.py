"""AUSHADHI — Gemini intelligence layer.

This module holds the ONLY two Gemini calls in the entire system:

    detect_outbreak()  — the "twist": epidemiological surveillance across all
                         health centers in a district, from consumption data
    forecast_demand()  — per-center, per-medicine demand + reorder prediction

Both prompts are reproduced verbatim from docs/AGENTS_SPEC.md (sections 3A and
3B) and were validated against live Gemini output in
scripts/test_gemini_outbreak.py. Do not paraphrase, reflow, or "improve" them.

Auth is Vertex AI (vertexai=True + Application Default Credentials), not an
AI Studio API key: the AI Studio free tier caps at 20 requests/day regardless
of billing, which one sentinel cycle can exhaust. Vertex bills the GCP project
directly and has no daily cap.

API config is otherwise the validated one from the same spec: the google-genai
SDK on gemini-3.5-flash with thinking_level="low" (thinking tokens share the
max_output_tokens budget — uncapped thinking silently truncates the JSON),
response_mime_type="application/json", and no temperature. Responses are
parsed with json.JSONDecoder().raw_decode() because Gemini occasionally
appends stray characters after the first complete JSON object.
"""

import asyncio
import json
import time
from collections import deque
from datetime import datetime
from functools import lru_cache
from statistics import mean
from typing import Any, Deque, Dict, List, Optional

from google import genai
from google.genai import types

from config import settings
from utils.logger import get_logger
from utils.retry import retry

log = get_logger(__name__)

# Gemini 503 UNAVAILABLE means server overload, not a client bug: wait ~8s and
# retry up to 4 attempts, exactly as scripts/test_gemini_outbreak.py does.
gemini_retry = retry(max_attempts=4, initial_delay=8.0, backoff_factor=2.0, max_delay=60.0)

OUTBREAK_MAX_OUTPUT_TOKENS = 8192
FORECAST_MAX_OUTPUT_TOKENS = 4096


class GeminiResponseError(RuntimeError):
    """Gemini returned no parseable JSON (empty, truncated, or malformed)."""


class GeminiQuotaExhaustedError(RuntimeError):
    """The daily free-tier request quota is gone — retrying today cannot help.

    Deliberately worded without "429" or "RESOURCE_EXHAUSTED" so utils.retry
    treats it as fatal instead of burning attempts on a limit that resets at
    midnight Pacific.
    """


class _RateLimiter:
    """Async sliding-window limiter, sized to the free tier's requests/minute.

    Both Gemini calls share one limiter, so the Forecast Agent's concurrent
    forecasts plus the outbreak call cannot collectively exceed the quota.
    """

    def __init__(self, max_per_minute: int) -> None:
        self._max = max(1, max_per_minute)
        self._window = 60.0
        self._calls: Deque[float] = deque()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        while True:
            async with self._lock:
                now = time.monotonic()
                while self._calls and now - self._calls[0] >= self._window:
                    self._calls.popleft()
                if len(self._calls) < self._max:
                    self._calls.append(now)
                    return
                wait_for = self._window - (now - self._calls[0]) + 0.05
            log.info("gemini_rate_limited", waiting_seconds=round(wait_for, 1), max_per_minute=self._max)
            await asyncio.sleep(wait_for)


# ══════════════════════════════════════════════════════════════════════════
#  SYSTEM PROMPTS — verbatim from docs/AGENTS_SPEC.md. DO NOT MODIFY.
# ══════════════════════════════════════════════════════════════════════════

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


FORECAST_SYSTEM_PROMPT = """You are AUSHADHI's demand forecasting intelligence for rural healthcare supply chains in India.

Your job is to analyze medicine consumption data from a health center and predict future demand accurately.

You understand Indian seasonal disease patterns:
- Monsoon (June-September): Malaria, Diarrhea, Cholera, Leptospirosis
- Winter (November-February): Respiratory infections, Influenza
- Summer (March-May): Heat stroke, Gastroenteritis, Typhoid
- Year-round: OPD visits, maternal health, routine medications

Return ONLY a valid JSON object. No markdown, no explanation, no preamble."""


# ══════════════════════════════════════════════════════════════════════════
#  SEASONAL / WEATHER CONTEXT
#  Static context for the prompt headers — AUSHADHI has no weather feed, and
#  the demo runs on the August 2026 monsoon scenario.
# ══════════════════════════════════════════════════════════════════════════

_SEASON_BY_MONTH = {
    1: "Winter", 2: "Winter",
    3: "Summer", 4: "Summer", 5: "Summer",
    6: "Monsoon", 7: "Monsoon", 8: "Monsoon", 9: "Monsoon",
    10: "Post-monsoon", 11: "Winter", 12: "Winter",
}
_PEAK_MONSOON_MONTHS = {7, 8}

_WEATHER_BY_DISTRICT = {
    "East Godavari": (
        "Heavy rainfall, flooding reported in low-lying areas near "
        "Krishna-Godavari delta"
    ),
    "West Godavari": "Heavy rainfall, waterlogging in delta mandals",
    "Krishna": "Heavy rainfall, river levels rising in the Krishna delta",
    "Guntur": "Intermittent heavy rainfall, localised waterlogging",
    "Visakhapatnam": "Coastal rainfall with occasional squalls",
}


def _is_daily_quota_error(exc: BaseException) -> bool:
    """True for the per-day free-tier limit, false for the per-minute one."""
    text = str(exc)
    return "429" in text and "PerDay" in text


def _parse_date(date: str) -> datetime:
    """Parse an ISO date/timestamp string, tolerating a trailing Z."""
    return datetime.fromisoformat(date.replace("Z", "+00:00"))


def get_season(date: str) -> str:
    """Season label for the outbreak prompt header, e.g. "Monsoon (August)"."""
    try:
        parsed = _parse_date(date)
    except ValueError:
        return "Unknown season"
    return f"{_SEASON_BY_MONTH[parsed.month]} ({parsed.strftime('%B')})"


def get_current_month(date: str) -> str:
    """Month label for the forecast prompt, e.g. "August (Monsoon peak)"."""
    try:
        parsed = _parse_date(date)
    except ValueError:
        return "Unknown month"
    season = _SEASON_BY_MONTH[parsed.month]
    suffix = f"{season} peak" if parsed.month in _PEAK_MONSOON_MONTHS else season
    return f"{parsed.strftime('%B')} ({suffix})"


def get_weather_context(district: str, date: Optional[str] = None) -> str:
    """Recent weather context for a district. Static — no weather feed wired up."""
    known = _WEATHER_BY_DISTRICT.get(district)
    if known:
        return known
    season = get_season(date).split(" (")[0] if date else "Unknown season"
    return f"No weather feed configured for {district}; season: {season}"


# ══════════════════════════════════════════════════════════════════════════
#  PROMPT BUILDERS — templates verbatim from docs/AGENTS_SPEC.md
# ══════════════════════════════════════════════════════════════════════════

def build_outbreak_prompt(district: str, centers_data: List[dict], date: str) -> str:
    centers_text = ""
    for center in centers_data:
        centers_text += f"\n{center['name']} ({center['type']}, {center['subdistrict']}):\n"
        for medicine in center['medicines']:
            if medicine.get('anomaly_flag') or medicine['consumption_ratio'] > 1.3:
                centers_text += (
                    f"  - {medicine['name']}: {medicine['current_consumption']} units "
                    f"(7d avg baseline: {medicine['baseline_consumption']}, "
                    f"ratio: {medicine['consumption_ratio']:.1f}x, "
                    f"anomaly: {medicine.get('anomaly_flag', False)})\n"
                )

    return f"""District: {district}, Andhra Pradesh
Date: {date}
Season: {get_season(date)} | Recent weather: {get_weather_context(district, date)}

CONSUMPTION ANOMALIES DETECTED THIS CYCLE:
{centers_text}

Total centers reporting anomalies: {len([c for c in centers_data if c.get('has_anomaly')])}
Total centers monitored: {len(centers_data)}

Analyze these consumption patterns for disease outbreak signals.
Return exactly this JSON structure:
{{
  "outbreak_detected": <boolean>,
  "risk_level": "<CRITICAL|HIGH|MEDIUM|LOW|NONE>",
  "disease_indicators": ["<CHOLERA|MALARIA|INFLUENZA|GASTROENTERITIS|DENGUE|OTHER>"],
  "affected_centers": ["<center_id_1>", "<center_id_2>"],
  "geographic_cluster": "<description of affected area>",
  "key_evidence": [
    {{
      "medicine": "<medicine_name>",
      "normal_daily_consumption": <number>,
      "current_daily_consumption": <number>,
      "ratio": <float>,
      "significance": "<HIGH|MEDIUM|LOW>"
    }}
  ],
  "confidence": <float 0.0-1.0>,
  "recommended_actions": [
    "<specific action 1>",
    "<specific action 2>"
  ],
  "outbreak_summary": "<one clear sentence for the district health officer>",
  "differential_diagnosis": "<other possible explanations for the pattern>",
  "recommended_surveillance_actions": ["<specific surveillance step>"]
}}"""


def _consumption_stats(consumption_history: List[dict]) -> Dict[str, Any]:
    """Derive the summary numbers the forecast prompt interpolates.

    seven_day_avg / thirty_day_avg are trailing means of daily_consumption.
    Trend compares the last 7 days against the 7 days before them. The anomaly
    flag is taken from the DQMS agent when it set one (docs/AGENTS_SPEC.md
    Agent 2 Rule 4), otherwise derived from latest-vs-prior-baseline.
    """
    daily = [float(r.get("daily_consumption", 0) or 0) for r in consumption_history]
    if not daily:
        return {
            "seven_day_avg": 0.0,
            "thirty_day_avg": 0.0,
            "trend_direction": "NO_DATA",
            "trend_percentage": 0.0,
            "anomaly_flag": False,
            "anomaly_ratio": 0.0,
        }

    seven_day_avg = mean(daily[-7:])
    thirty_day_avg = mean(daily[-30:])

    prior_window = daily[-14:-7]
    prior_avg = mean(prior_window) if prior_window else 0.0
    if prior_avg > 0:
        trend_percentage = (seven_day_avg - prior_avg) / prior_avg * 100
    else:
        trend_percentage = 0.0

    if trend_percentage >= 50:
        trend_direction = "SHARPLY_INCREASING"
    elif trend_percentage >= 15:
        trend_direction = "INCREASING"
    elif trend_percentage <= -50:
        trend_direction = "SHARPLY_DECREASING"
    elif trend_percentage <= -15:
        trend_direction = "DECREASING"
    else:
        trend_direction = "STABLE"

    latest = consumption_history[-1]
    baseline = prior_avg or thirty_day_avg
    derived_ratio = (daily[-1] / baseline) if baseline > 0 else 0.0
    anomaly_ratio = float(latest.get("anomaly_ratio") or derived_ratio)
    anomaly_flag = bool(latest.get("anomaly_flag", anomaly_ratio >= 3.0))

    return {
        "seven_day_avg": seven_day_avg,
        "thirty_day_avg": thirty_day_avg,
        "trend_direction": trend_direction,
        "trend_percentage": trend_percentage,
        "anomaly_flag": anomaly_flag,
        "anomaly_ratio": anomaly_ratio,
    }


def build_forecast_prompt(center: dict, medicine: dict, consumption_history: list) -> str:
    history_text = "\n".join([
        f"  {r['date']}: consumed {r['daily_consumption']} units, opening stock {r['opening_stock']}"
        for r in consumption_history[-14:]  # Last 14 days
    ])

    stats = _consumption_stats(consumption_history)
    seven_day_avg = stats["seven_day_avg"]
    thirty_day_avg = stats["thirty_day_avg"]
    trend_direction = stats["trend_direction"]
    trend_percentage = stats["trend_percentage"]
    anomaly_flag = stats["anomaly_flag"]
    anomaly_ratio = stats["anomaly_ratio"]

    as_of = consumption_history[-1]["date"] if consumption_history else datetime.utcnow().date().isoformat()
    current_month = get_current_month(str(as_of))

    return f"""Health Center: {center['name']} ({center['type']}) — {center['district']} District, Andhra Pradesh
Medicine: {medicine['name']} ({medicine['category']})
Current Stock: {medicine['current_stock']} units
Minimum Threshold: {medicine['minimum_threshold']} units
Maximum Capacity: {medicine['maximum_capacity']} units
Current Month: {current_month}
Catchment Population: {center['catchment_population']:,}

Consumption History (last 14 days):
{history_text}

7-day average daily consumption: {seven_day_avg:.1f} units
30-day average daily consumption: {thirty_day_avg:.1f} units
Trend: {trend_direction} ({trend_percentage:+.1f}% vs previous period)
Anomaly flag: {anomaly_flag} (ratio: {anomaly_ratio:.1f}x if flagged)

Predict demand and reorder requirements. Return exactly this JSON structure:
{{
  "predicted_daily_consumption_next_7_days": <number>,
  "predicted_daily_consumption_next_30_days": <number>,
  "days_until_stockout_at_current_trend": <integer>,
  "reorder_urgency": "<CRITICAL|HIGH|MEDIUM|LOW>",
  "recommended_order_quantity": <integer>,
  "forecast_confidence": <float 0.0-1.0>,
  "seasonal_adjustment": "<increase|decrease|stable>",
  "seasonal_reasoning": "<one sentence>",
  "forecasting_reasoning": "<one sentence explaining the prediction>"
}}"""


# ══════════════════════════════════════════════════════════════════════════
#  SERVICE
# ══════════════════════════════════════════════════════════════════════════

class GeminiService:
    """The two — and only two — Gemini calls in AUSHADHI."""

    def __init__(self, client: Optional[genai.Client] = None) -> None:
        # Vertex AI, not AI Studio: an AI Studio key is capped at 20 requests/day
        # on the free tier regardless of billing, which a single sentinel cycle
        # can exhaust. Vertex bills the GCP project directly and authenticates
        # with Application Default Credentials, so no API key is used here.
        self.settings = settings
        self._client = client or genai.Client(
            vertexai=True,
            project=settings.google_cloud_project,
            location=settings.vertex_location,
        )
        self._model = settings.gemini_model
        # Built on first Gemma call, then reused. Gemma answers from a
        # regional endpoint, so it needs a second client with its own location.
        self._gemma_client: Optional[genai.Client] = None
        self._limiter = _RateLimiter(settings.gemini_max_requests_per_minute)
        log.info(
            "gemini_service_initialized",
            model=self._model,
            auth="vertex_ai_adc",
            project=settings.google_cloud_project,
            location=settings.vertex_location,
            gemma_fallback=settings.use_gemma_fallback,
            max_requests_per_minute=settings.gemini_max_requests_per_minute,
        )

    @property
    def client(self) -> genai.Client:
        return self._client

    @property
    def active_model(self) -> str:
        """The model the next call will use — Gemma when the toggle is on."""
        return self._get_client_and_model()[1]

    # ─────────────────────── model selection / fallback ─────────────────

    def _get_client_and_model(self) -> tuple:
        """Return (client, model_name, is_gemma) for the current settings.

        Read on every call rather than fixed at construction, so flipping
        use_gemma_fallback (PATCH /api/v1/config) takes effect on the next
        Gemini call without a restart. The injected client passed to
        __init__ still wins for Gemini so tests can stub it.
        """
        if getattr(self.settings, "use_gemma_fallback", False):
            if self._gemma_client is None:
                # Gemma is served from a regional endpoint; vertex_location is
                # "global", which is Gemini-only and 404s for Gemma.
                self._gemma_client = genai.Client(
                    vertexai=True,
                    project=self.settings.google_cloud_project,
                    location=self.settings.google_cloud_region,
                )
                log.info(
                    "gemini_gemma_client_created",
                    model=self.settings.gemma_model,
                    location=self.settings.google_cloud_region,
                )
            return self._gemma_client, self.settings.gemma_model, True
        return self._client, self._model, False

    # ────────────────────────── internal call ──────────────────────────

    def _generate(self, prompt: str, system_prompt: str, max_output_tokens: int):
        """Blocking model call with the validated config from AGENTS_SPEC.md."""
        client, model, is_gemma = self._get_client_and_model()
        try:
            return self._call(client, model, is_gemma, prompt, system_prompt, max_output_tokens)
        except Exception as exc:
            if _is_daily_quota_error(exc):
                raise GeminiQuotaExhaustedError(
                    "Gemini daily free-tier request limit reached for "
                    f"{model}; enable billing or wait for the quota reset"
                ) from exc
            raise

    def _call(
        self,
        client: genai.Client,
        model: str,
        is_gemma: bool,
        prompt: str,
        system_prompt: str,
        max_output_tokens: int,
    ):
        if is_gemma:
            # Gemma takes none of the three Gemini-only options below: it has
            # no thinking budget, no JSON response mode, and no system role.
            # Sending them is a 400, so the system prompt is prepended to the
            # user turn and the JSON contract is left to the prompt itself
            # (_parse strips the markdown fence Gemma tends to add).
            return client.models.generate_content(
                model=model,
                contents=f"{system_prompt}\n\n{prompt}",
                config=types.GenerateContentConfig(max_output_tokens=max_output_tokens),
            )
        return client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                max_output_tokens=max_output_tokens,
                response_mime_type="application/json",
                thinking_config=types.ThinkingConfig(
                    thinking_level=settings.gemini_thinking_level
                ),
            ),
        )

    @staticmethod
    def _parse(response, operation: str) -> Dict[str, Any]:
        """raw_decode the first complete JSON object; ignore any trailing junk."""
        text = (response.text or "").strip()
        if not text:
            finish_reason = (
                response.candidates[0].finish_reason if response.candidates else "unknown"
            )
            raise GeminiResponseError(
                f"{operation}: empty Gemini response (finish_reason={finish_reason})"
            )
        # Gemini answers with response_mime_type="application/json" and never
        # fences its output; Gemma has no JSON mode and usually wraps it in
        # ```json ... ```, which raw_decode cannot start on.
        if text.startswith("```"):
            text = text.split("\n", 1)[-1] if "\n" in text else text[3:]
            fence = text.rfind("```")
            if fence != -1:
                text = text[:fence]
            text = text.strip()
        decoder = json.JSONDecoder()
        try:
            result, _end_index = decoder.raw_decode(text)
        except json.JSONDecodeError as exc:
            raise GeminiResponseError(
                f"{operation}: could not parse Gemini JSON ({exc}); raw={text[:500]}"
            ) from exc
        if not isinstance(result, dict):
            raise GeminiResponseError(
                f"{operation}: expected a JSON object, got {type(result).__name__}"
            )
        return result

    @staticmethod
    def _token_counts(response) -> Dict[str, Any]:
        usage = getattr(response, "usage_metadata", None)
        if usage is None:
            return {}
        return {
            "prompt_tokens": getattr(usage, "prompt_token_count", None),
            "output_tokens": getattr(usage, "candidates_token_count", None),
            "thinking_tokens": getattr(usage, "thoughts_token_count", None),
        }

    # ───────────────────────── 1. OUTBREAK DETECTION ────────────────────

    @gemini_retry
    async def detect_outbreak(
        self,
        centers_data: List[dict],
        district: str,
        date: str,
    ) -> Dict[str, Any]:
        """Detect disease outbreak signals across every center in a district.

        Runs ONCE per sentinel cycle with all centers' consumption anomalies in
        a single prompt — the cross-center view is what makes clustering
        detectable. Returns the parsed JSON dict; raises on unparseable output.
        """
        prompt = build_outbreak_prompt(district, centers_data, date)

        await self._limiter.acquire()
        started = time.perf_counter()
        response = await asyncio.to_thread(
            self._generate, prompt, OUTBREAK_SYSTEM_PROMPT, OUTBREAK_MAX_OUTPUT_TOKENS
        )
        duration_ms = int((time.perf_counter() - started) * 1000)

        result = self._parse(response, "detect_outbreak")

        # The prompt (frozen per AGENTS_SPEC.md) carries center names but not
        # center_ids, so Gemini answers with names. Map them back to ids the
        # agents can write into OutbreakAlert.affected_centers; anything that
        # doesn't match a known center is left as-is.
        name_to_id = {
            c["name"]: (c.get("id") or c.get("center_id")) for c in centers_data if c.get("name")
        }
        result["affected_centers"] = [
            name_to_id.get(name) or name for name in result.get("affected_centers", [])
        ]

        log.info(
            "gemini_outbreak_detection",
            model=self.active_model,
            district=district,
            date=date,
            centers_analyzed=len(centers_data),
            outbreak_detected=result.get("outbreak_detected"),
            risk_level=result.get("risk_level"),
            disease_indicators=result.get("disease_indicators"),
            confidence=result.get("confidence"),
            duration_ms=duration_ms,
            **self._token_counts(response),
        )
        return result

    # ───────────────────────── 2. DEMAND FORECASTING ────────────────────

    @gemini_retry
    async def forecast_demand(
        self,
        center: dict,
        medicine: dict,
        consumption_history: list,
    ) -> Dict[str, Any]:
        """Predict 7/30-day demand and reorder requirements for one medicine."""
        prompt = build_forecast_prompt(center, medicine, consumption_history)

        await self._limiter.acquire()
        started = time.perf_counter()
        response = await asyncio.to_thread(
            self._generate, prompt, FORECAST_SYSTEM_PROMPT, FORECAST_MAX_OUTPUT_TOKENS
        )
        duration_ms = int((time.perf_counter() - started) * 1000)

        result = self._parse(response, "forecast_demand")

        log.info(
            "gemini_demand_forecast",
            model=self.active_model,
            center_id=center.get("id") or center.get("center_id"),
            medicine_id=medicine.get("id") or medicine.get("medicine_id"),
            medicine_name=medicine.get("name"),
            history_days=len(consumption_history),
            reorder_urgency=result.get("reorder_urgency"),
            days_until_stockout=result.get("days_until_stockout_at_current_trend"),
            recommended_order_quantity=result.get("recommended_order_quantity"),
            forecast_confidence=result.get("forecast_confidence"),
            duration_ms=duration_ms,
            **self._token_counts(response),
        )
        return result


@lru_cache
def get_gemini_service() -> GeminiService:
    """Process-wide GeminiService singleton."""
    return GeminiService()
