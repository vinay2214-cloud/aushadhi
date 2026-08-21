"""AUSHADHI — recorded Gemini responses for offline pipeline runs.

NOT a mock of convenience: both payloads below are verbatim live responses
captured from gemini-3.5-flash earlier today by
scripts/test_gemini_service.py and the forecast_demand check. They exist so
the Pub/Sub -> Firestore chain can be exercised when the API key's free-tier
daily quota (20 requests) is spent.

RecordedGeminiService still builds the real prompts through
services.gemini_service, so prompt construction is exercised for real; only
the network call is replaced. Anything it returns is a REPLAY, not a fresh
model judgment — rerun with the live service before trusting a verdict.
"""

from typing import Any, Dict, List

from services.gemini_service import build_forecast_prompt, build_outbreak_prompt
from utils.logger import get_logger

log = get_logger(__name__)

# Live response, 2026-08-20, Razole/Amalapuram/CHC Razole cholera scenario.
RECORDED_OUTBREAK = {
    "outbreak_detected": True,
    "risk_level": "HIGH",
    "disease_indicators": ["CHOLERA"],
    "affected_centers": ["PHC Razole", "PHC Amalapuram"],
    "geographic_cluster": (
        "Razole and Amalapuram mandals in the low-lying Krishna-Godavari delta "
        "region of East Godavari"
    ),
    "key_evidence": [
        {
            "medicine": "ORS Packets (WHO Formula)",
            "normal_daily_consumption": 20,
            "current_daily_consumption": 76,
            "ratio": 3.8,
            "significance": "HIGH",
        },
        {
            "medicine": "Zinc Tablets 20mg",
            "normal_daily_consumption": 50,
            "current_daily_consumption": 190,
            "ratio": 3.8,
            "significance": "HIGH",
        },
        {
            "medicine": "IV Normal Saline 500ml",
            "normal_daily_consumption": 5,
            "current_daily_consumption": 19,
            "ratio": 3.8,
            "significance": "HIGH",
        },
    ],
    "confidence": 0.92,
    "recommended_actions": [
        "Dispatch rapid response epidemiological teams to Razole and Amalapuram to "
        "collect water samples and stool specimens.",
        "Deploy temporary chlorination units and distribute water purification tablets "
        "to flood-affected households in the cluster area.",
        "Pre-position extra stocks of IV fluids, ORS, and zinc at PHC Razole and "
        "PHC Amalapuram.",
        "Notify IDSP — cholera is a notifiable disease event.",
    ],
    "outbreak_summary": (
        "A highly localized cluster of health centers in the flood-affected "
        "Razole-Amalapuram area is showing a coordinated 3.8x surge in ORS, Zinc, and "
        "IV fluid consumption, pointing to an emerging cholera or severe waterborne "
        "diarrheal outbreak."
    ),
    "differential_diagnosis": (
        "Non-cholera bacterial or viral gastroenteritis exacerbated by flood-related "
        "water contamination, though the high ratio of IV fluid and Zinc consumption "
        "strongly flags severe dehydration typical of cholera."
    ),
    "recommended_surveillance_actions": [
        "Initiate active daily door-to-door case search for severe watery diarrhea in "
        "the affected mandals.",
        "Establish daily sentinel reporting on diarrhea cases from all private and "
        "public clinics in Razole and Amalapuram.",
    ],
}

# Live response, 2026-08-20, PHC Razole / ORS Packets.
RECORDED_FORECAST = {
    "predicted_daily_consumption_next_7_days": 48.0,
    "predicted_daily_consumption_next_30_days": 42.0,
    "days_until_stockout_at_current_trend": 1,
    "reorder_urgency": "CRITICAL",
    "recommended_order_quantity": 555,
    "forecast_confidence": 0.95,
    "seasonal_adjustment": "increase",
    "seasonal_reasoning": (
        "Monsoon peak in East Godavari drives high rates of waterborne diseases and "
        "diarrheal infections, drastically elevating ORS demand."
    ),
    "forecasting_reasoning": (
        "With current stock at 45 units and daily consumption spiking to 46 units, a "
        "stockout is imminent within 24 hours, requiring immediate replenishment."
    ),
}

# A district with no cholera signature gets the low-risk shape instead.
RECORDED_NO_OUTBREAK = {
    "outbreak_detected": False,
    "risk_level": "LOW",
    "disease_indicators": [],
    "affected_centers": [],
    "geographic_cluster": "No geographic clustering detected",
    "key_evidence": [],
    "confidence": 0.35,
    "recommended_actions": ["Continue routine monitoring"],
    "outbreak_summary": "No outbreak signature detected in this district's consumption data.",
    "differential_diagnosis": "Consumption variation consistent with seasonal baseline.",
    "recommended_surveillance_actions": ["Maintain weekly consumption review"],
}

OUTBREAK_DISTRICT = "East Godavari"


class RecordedGeminiService:
    """Drop-in for GeminiService that replays captured responses."""

    def __init__(self) -> None:
        self.forecast_calls = 0
        self.outbreak_calls = 0
        log.warning(
            "gemini_recorded_mode",
            note="replaying captured live responses — no Gemini request is made",
        )

    async def forecast_demand(
        self, center: dict, medicine: dict, consumption_history: list
    ) -> Dict[str, Any]:
        prompt = build_forecast_prompt(center, medicine, consumption_history)
        self.forecast_calls += 1

        # Scale the recorded quantity to this medicine's own capacity so the
        # purchase orders stay internally consistent.
        capacity = int(medicine.get("maximum_capacity") or 0)
        stock = int(medicine.get("current_stock") or 0)
        quantity = max(capacity - stock, 1) if capacity else RECORDED_FORECAST[
            "recommended_order_quantity"
        ]

        log.info(
            "gemini_recorded_forecast",
            center_id=center.get("id"),
            medicine=medicine.get("name"),
            prompt_chars=len(prompt),
            recommended_order_quantity=quantity,
        )
        return {**RECORDED_FORECAST, "recommended_order_quantity": quantity}

    async def detect_outbreak(
        self, centers_data: List[dict], district: str, date: str
    ) -> Dict[str, Any]:
        prompt = build_outbreak_prompt(district, centers_data, date)
        self.outbreak_calls += 1

        anomalous = [c for c in centers_data if c.get("has_anomaly")]
        result = dict(
            RECORDED_OUTBREAK if district == OUTBREAK_DISTRICT and anomalous
            else RECORDED_NO_OUTBREAK
        )

        # Same name -> id mapping the live service applies after raw_decode.
        name_to_id = {
            c["name"]: (c.get("id") or c.get("center_id")) for c in centers_data if c.get("name")
        }
        result["affected_centers"] = [
            name_to_id.get(name) or name for name in result.get("affected_centers", [])
        ]

        log.info(
            "gemini_recorded_outbreak",
            district=district,
            centers=len(centers_data),
            prompt_chars=len(prompt),
            risk_level=result["risk_level"],
            affected_centers=result["affected_centers"],
        )
        return result
