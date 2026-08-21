# AUSHADHI — Agent Specifications
### The Exact Prompts, Behaviors, and Pipelines

> This is the most critical document. The Gemini prompts here are final.
> Do not alter them without updating this file.
> Framework: Google ADK + Antigravity SDK | Model: Gemini 1.5 Flash

---

## PIPELINE OVERVIEW

```
Cloud Scheduler (every 30 min)
         │
         ▼
[1] SENTINEL AGENT
    Polls all health center inventory
    Identifies centers below threshold
    Publishes to: aushadhi-sentinel-alerts
         │
         ▼
[2] DQMS VALIDATION AGENT  ← Your DQMS expertise lives here
    Validates consumption data quality
    Rejects/flags bad records
    Publishes to: aushadhi-validated-data
         │
         ▼
[3] FORECAST + OUTBREAK AGENT  ← The Twist lives here
    Gemini predicts demand per medicine
    Gemini detects outbreak patterns from consumption
    Publishes to: aushadhi-forecast-complete
         │
    ┌────┴────┐
    ▼         ▼
[4] PROCUREMENT   [5] ALERT + REPORT
    AGENT          AGENT
    Auto-generates  Notifies district
    purchase orders officer + generates
                   compliance report
```

---

## AGENT 1: INVENTORY SENTINEL AGENT

**File:** `backend/agents/sentinel_agent.py`  
**Trigger:** Cloud Scheduler (every 30 minutes) + manual API call  
**Uses Gemini:** NO — pure Python logic  

**Behavior:**
```
For each health center in Firestore:
  For each medicine tracked at that center:
    1. Read current_stock and minimum_threshold from inventory collection
    2. Calculate stock_percentage = current_stock / maximum_stock * 100
    3. Classify urgency:
       - CRITICAL: stock_percentage < 15%
       - LOW: stock_percentage < 30%
       - MONITOR: stock_percentage < 50%
       - OK: stock_percentage >= 50%
    4. If urgency is CRITICAL or LOW:
       - Create alert record in Firestore (sentinel_alerts collection)
       - Publish to aushadhi-sentinel-alerts Pub/Sub topic
    5. Update last_checked timestamp on health center
```

**Pub/Sub Message Published:**
```json
{
  "center_id": "phc_razole_001",
  "center_name": "PHC Razole",
  "district": "East Godavari",
  "critical_items": [
    {
      "medicine_id": "med_ors_001",
      "medicine_name": "ORS Packets",
      "current_stock": 45,
      "minimum_threshold": 200,
      "stock_percentage": 8.2,
      "urgency": "CRITICAL"
    }
  ],
  "low_items": [...],
  "total_critical": 2,
  "total_low": 3,
  "timestamp": "2026-08-20T08:00:00Z",
  "action": "VALIDATION_AND_FORECAST_REQUIRED"
}
```

**Error Handling:**
- If Firestore read fails: log error, skip that center, continue others
- If center has no inventory records: flag as "NO_DATA", skip pipeline

---

## AGENT 2: DQMS VALIDATION AGENT

**File:** `backend/agents/dqms_agent.py`  
**Trigger:** Subscribes to `aushadhi-sentinel-alerts`  
**Uses Gemini:** NO — deterministic validation rules  
**This is where your DQMS expertise is directly reused.**

**Validation Rules (implement exactly):**

```python
class ConsumptionValidator:
    """Port of DQMS validation logic applied to health center consumption data."""
    
    def validate_consumption_record(self, record: dict) -> ValidationResult:
        errors = []
        warnings = []
        quality_score = 1.0
        
        # Rule 1: Stock cannot be negative
        if record.get('current_stock', 0) < 0:
            errors.append("NEGATIVE_STOCK: current_stock cannot be negative")
            quality_score -= 0.3
        
        # Rule 2: Daily consumption cannot exceed opening stock
        if record.get('daily_consumption', 0) > record.get('opening_stock', 0):
            errors.append("IMPOSSIBLE_CONSUMPTION: consumed more than opening stock")
            quality_score -= 0.4
        
        # Rule 3: Missing report flag (no data for 48+ hours)
        hours_since_update = (now - record.get('last_updated')).total_seconds() / 3600
        if hours_since_update > 48:
            warnings.append(f"STALE_DATA: {hours_since_update:.0f}h since last update")
            quality_score -= 0.2
        
        # Rule 4: Statistical anomaly (consumption > 3x 7-day average)
        seven_day_avg = record.get('seven_day_avg_consumption', 0)
        if seven_day_avg > 0:
            ratio = record.get('daily_consumption', 0) / seven_day_avg
            if ratio > 5.0:
                warnings.append(f"ANOMALY: consumption is {ratio:.1f}x the 7-day average")
                # NOTE: This is a FEATURE, not a bug — high ratio may indicate outbreak
                # Pass to forecast agent with anomaly flag set
                record['anomaly_flag'] = True
                record['anomaly_ratio'] = ratio
            elif ratio < 0.1 and seven_day_avg > 10:
                warnings.append("SUSPICIOUS_LOW: consumption unexpectedly very low (under-reporting?)")
                quality_score -= 0.1
        
        # Rule 5: Duplicate record check
        # Query Firestore for same center + medicine + date combination
        # If duplicate found: flag and use the higher-quality record
        
        # Rule 6: Required fields present
        required = ['center_id', 'medicine_id', 'current_stock', 'daily_consumption', 'report_date']
        for field in required:
            if field not in record or record[field] is None:
                errors.append(f"MISSING_FIELD: {field} is required")
                quality_score -= 0.15
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            quality_score=max(0.0, quality_score),
            processed_record=record
        )
    
    def validate_center_batch(self, center_id: str, records: list) -> BatchResult:
        """Validate all records for a health center."""
        results = [self.validate_consumption_record(r) for r in records]
        center_quality_score = sum(r.quality_score for r in results) / len(results)
        valid_records = [r.processed_record for r in results if r.is_valid]
        rejected_records = [r for r in results if not r.is_valid]
        return BatchResult(
            center_id=center_id,
            total_records=len(records),
            valid_records=len(valid_records),
            rejected_records=len(rejected_records),
            center_quality_score=center_quality_score,
            anomalies_detected=[r for r in results if r.processed_record.get('anomaly_flag')]
        )
```

**Pub/Sub Message Published:**
```json
{
  "center_id": "phc_razole_001",
  "validation_summary": {
    "total_records": 12,
    "valid_records": 11,
    "rejected_records": 1,
    "center_quality_score": 0.87,
    "anomalies_detected": [
      {
        "medicine_id": "med_ors_001",
        "anomaly_ratio": 3.8,
        "anomaly_flag": true
      }
    ]
  },
  "validated_inventory": [...],
  "rejected_records": [...],
  "action": "FORECAST_REQUIRED"
}
```

---

## AGENT 3: FORECAST + OUTBREAK DETECTION AGENT

**File:** `backend/agents/forecast_agent.py`  
**Trigger:** Subscribes to `aushadhi-validated-data`  
**Uses Gemini:** YES — Gemini 1.5 Flash  
**THIS IS THE HEART OF AUSHADHI. These prompts are final.**

### 3A: DEMAND FORECASTING PROMPT

**System Prompt (exact, do not modify):**
```
You are AUSHADHI's demand forecasting intelligence for rural healthcare supply chains in India.

Your job is to analyze medicine consumption data from a health center and predict future demand accurately.

You understand Indian seasonal disease patterns:
- Monsoon (June-September): Malaria, Diarrhea, Cholera, Leptospirosis
- Winter (November-February): Respiratory infections, Influenza
- Summer (March-May): Heat stroke, Gastroenteritis, Typhoid
- Year-round: OPD visits, maternal health, routine medications

Return ONLY a valid JSON object. No markdown, no explanation, no preamble.
```

**User Prompt (built dynamically):**
```python
def build_forecast_prompt(center: dict, medicine: dict, consumption_history: list) -> str:
    history_text = "\n".join([
        f"  {r['date']}: consumed {r['daily_consumption']} units, opening stock {r['opening_stock']}"
        for r in consumption_history[-14:]  # Last 14 days
    ])
    
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
```

**Expected Response:**
```json
{
  "predicted_daily_consumption_next_7_days": 28,
  "predicted_daily_consumption_next_30_days": 35,
  "days_until_stockout_at_current_trend": 4,
  "reorder_urgency": "CRITICAL",
  "recommended_order_quantity": 500,
  "forecast_confidence": 0.87,
  "seasonal_adjustment": "increase",
  "seasonal_reasoning": "August is peak monsoon season in East Godavari — ORS demand historically 200-280% of baseline due to diarrheal disease burden.",
  "forecasting_reasoning": "14-day trend shows 3.8x consumption increase with anomaly flag, consistent with a disease event rather than routine demand variation."
}
```

---

### 3B: OUTBREAK DETECTION PROMPT

**This is the "Twist". This runs ONCE per sentinel cycle across ALL health centers together.**

**System Prompt (exact, do not modify):**
```
You are AUSHADHI's epidemiological surveillance intelligence for Andhra Pradesh, India.

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

Return ONLY valid JSON. No markdown, no preamble, no explanation outside the JSON.
```

**User Prompt (built dynamically with ALL centers' data):**
```python
def build_outbreak_prompt(district: str, centers_data: list, date: str) -> str:
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
Season: {get_season(date)} | Recent weather: {get_weather_context(district)}

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
```

**Expected Response (when outbreak detected):**
```json
{
  "outbreak_detected": true,
  "risk_level": "HIGH",
  "disease_indicators": ["CHOLERA"],
  "affected_centers": ["phc_razole_001", "phc_amalapuram_002", "chc_razole_003"],
  "geographic_cluster": "Razole mandal and surrounding area, East Godavari — near Krishna-Godavari delta",
  "key_evidence": [
    {
      "medicine": "ORS Packets",
      "normal_daily_consumption": 12,
      "current_daily_consumption": 46,
      "ratio": 3.8,
      "significance": "HIGH"
    },
    {
      "medicine": "Zinc Tablets",
      "normal_daily_consumption": 8,
      "current_daily_consumption": 29,
      "ratio": 3.6,
      "significance": "HIGH"
    },
    {
      "medicine": "IV Normal Saline",
      "normal_daily_consumption": 3,
      "current_daily_consumption": 11,
      "ratio": 3.7,
      "significance": "HIGH"
    }
  ],
  "confidence": 0.89,
  "recommended_actions": [
    "Immediately dispatch emergency ORS + IV fluid stock to PHC Razole and PHC Amalapuram",
    "Alert District Medical Officer East Godavari for rapid response team deployment",
    "Notify IDSP (Integrated Disease Surveillance Programme) — Cholera is a notifiable disease",
    "Conduct water quality testing in Razole mandal — likely contaminated water source"
  ],
  "outbreak_summary": "High-confidence cholera/severe diarrhea cluster detected in Razole mandal based on simultaneous ORS+Zinc+IV fluid consumption spike (3.6–3.8x baseline) across 3 health facilities.",
  "differential_diagnosis": "Could be severe gastroenteritis cluster or mass food poisoning event; cholera most likely given IV fluid involvement and geographic pattern near water bodies",
  "recommended_surveillance_actions": [
    "Collect stool samples from 5 recent diarrhea patients at PHC Razole for Vibrio cholerae culture",
    "Map all water sources within 5km radius of affected centers"
  ]
}
```

**Gemini API Config (both prompts):**
```python
generation_config = genai.types.GenerationConfig(
    temperature=0.05,              # Very low — we want deterministic clinical decisions
    max_output_tokens=1024,
    response_mime_type="application/json"   # Force JSON output
)
safety_settings = [
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_ONLY_HIGH"}
]
```

---

## AGENT 4: PROCUREMENT AGENT

**File:** `backend/agents/procurement_agent.py`  
**Trigger:** Subscribes to `aushadhi-forecast-complete`  
**Uses Gemini:** NO — deterministic logic  
**CrisisRoute expertise: nearest-warehouse routing reused here**

**Behavior:**
```
For each CRITICAL or HIGH urgency item from Forecast Agent:
  1. Find nearest warehouse with sufficient stock
     (same haversine distance logic as CrisisRoute)
  2. Generate Purchase Order document:
     - PO number (auto-generated: AUSD-{YYYYMMDD}-{sequence})
     - Health center details
     - Line items: medicine, quantity, unit cost
     - Nearest warehouse details + estimated delivery time
     - Priority classification
  3. Write PO to Firestore (purchase_orders collection)
  4. Update inventory record: expected_stock_date set
  5. Publish to aushadhi-procured topic
```

**Purchase Order Schema:**
```python
{
  "po_number": "AUSD-20260820-0047",
  "generated_at": "2026-08-20T08:12:34Z",
  "generated_by": "AUSHADHI_PROCUREMENT_AGENT",
  "priority": "CRITICAL",          # From forecast urgency
  "health_center": {
    "id": "phc_razole_001",
    "name": "PHC Razole",
    "district": "East Godavari",
    "address": "Razole, East Godavari, AP 533242"
  },
  "nearest_warehouse": {
    "id": "wh_rajahmundry_001",
    "name": "District Medical Stores, Rajahmundry",
    "distance_km": 42,
    "estimated_delivery_hours": 6
  },
  "line_items": [
    {
      "medicine_id": "med_ors_001",
      "medicine_name": "ORS Packets (WHO formula)",
      "requested_quantity": 500,
      "unit": "packets",
      "estimated_unit_cost_inr": 3.50,
      "total_cost_inr": 1750.00,
      "urgency": "CRITICAL",
      "days_until_stockout": 4
    }
  ],
  "total_cost_inr": 1750.00,
  "status": "PENDING_APPROVAL",
  "approval_required": true,        # District officer must approve
  "auto_approved": false,
  "outbreak_linked": true,          # Linked to outbreak alert
  "outbreak_alert_id": "outbreak_abc123"
}
```

**Routing Algorithm (from CrisisRoute):**
```python
def find_nearest_warehouse(center_location: dict, medicine_id: str, quantity: int) -> dict:
    """Find nearest warehouse with sufficient stock."""
    available_warehouses = query_warehouses_with_stock(medicine_id, quantity)
    
    scored = []
    for wh in available_warehouses:
        distance_km = haversine(
            (center_location['lat'], center_location['lng']),
            (wh['location']['lat'], wh['location']['lng']),
            unit='km'
        )
        # Estimate delivery: 60km/h average, add loading time
        eta_hours = (distance_km / 60) + 2
        scored.append({**wh, 'distance_km': distance_km, 'eta_hours': eta_hours})
    
    return min(scored, key=lambda w: w['distance_km'])
```

---

## AGENT 5: ALERT + REPORT AGENT

**File:** `backend/agents/alert_agent.py`  
**Trigger:** Subscribes to `aushadhi-procured`  
**Uses Gemini:** NO — template-based  

**Three notification types:**

**Stockout Alert to Medical Officer:**
```
AUSHADHI Alert — PHC Razole | East Godavari

⚠ CRITICAL STOCKOUT WARNING ⚠

The following medicines are at CRITICAL levels (< 15% stock):
• ORS Packets: 45 units remaining (4 days supply at current rate)
• Zinc Tablets: 32 units remaining (3 days supply)
• IV Normal Saline: 8 units remaining (CRITICAL — 2 days supply)

AUTOMATED ACTION TAKEN:
Purchase Order AUSD-20260820-0047 generated
Nearest warehouse: District Medical Stores, Rajahmundry (42 km)
Estimated delivery: Within 6 hours of approval

ACTION REQUIRED FROM YOU:
Please approve PO AUSD-20260820-0047 at [dashboard URL]

AUSHADHI System | East Godavari District Health Programme
```

**Outbreak Alert to District Health Officer:**
```
AUSHADHI OUTBREAK INTELLIGENCE ALERT
District: East Godavari | Priority: HIGH | Confidence: 89%

DETECTED PATTERN: CHOLERA / SEVERE DIARRHEAL DISEASE CLUSTER

Affected areas: Razole mandal (3 facilities)
Evidence: ORS consumption 3.8x baseline, Zinc 3.6x, IV Saline 3.7x
Timeline: Pattern emerged over past 72 hours

IMMEDIATE RECOMMENDED ACTIONS:
1. Deploy Rapid Response Team to Razole mandal
2. Emergency ORS/IV fluid stock dispatch initiated (PO auto-generated)
3. Notify IDSP — this is a notifiable disease event
4. Water quality testing required — Razole area water sources

This alert was generated by AUSHADHI before any patient was officially reported.
Estimated lead time advantage over manual surveillance: 3-5 days

For full analysis: [dashboard URL]/outbreaks/[outbreak_id]
```

**Weekly Compliance Report (auto-generated every Monday):**
```
AUSHADHI Weekly Supply Intelligence Report
District: East Godavari | Period: Aug 14-20, 2026

SUPPLY STATUS SUMMARY:
• Facilities monitored: 8
• Critical stockouts prevented: 3 (via automated POs)
• Purchase orders generated: 7 (total value: ₹42,340)
• Data quality score: 87.3% (up from 82.1% last week)

OUTBREAK INTELLIGENCE:
• Alerts generated: 1 (Razole mandal, Cholera/Diarrheal — HIGH)
• Status: Confirmed and under response
• Lead time vs manual detection: Estimated 3-4 days

MEDICINE CONSUMPTION TRENDS:
• ORS: 285% above baseline (Razole area) — outbreak-linked
• Paracetamol: 12% above baseline — seasonal (monsoon ILI)
• All other essential medicines: within normal range

[Full report: 8 pages — see attached PDF]
```

---

## ORCHESTRATOR

**File:** `backend/agents/orchestrator.py`

```python
class AushdhiOrchestrator:
    """Manages all 5 agents and their Pub/Sub routing."""
    
    subscriptions = {
        "aushadhi-sentinel-alerts-sub": DQMSValidationAgent,
        "aushadhi-validated-data-sub": ForecastOutbreakAgent,
        "aushadhi-forecast-complete-sub": ProcurementAgent,
        "aushadhi-procured-sub": AlertReportAgent,
    }
    
    async def run_sentinel_cycle(self):
        """Called by Cloud Scheduler every 30 minutes."""
        await self.sentinel_agent.scan_all_centers()
    
    async def start_subscribers(self):
        """Start all Pub/Sub subscribers."""
        tasks = [
            self._subscribe(sub, agent_class())
            for sub, agent_class in self.subscriptions.items()
        ]
        await asyncio.gather(*tasks)
```

---

## GEMMA INTEGRATION (Bonus Points)

**When:** When internet connectivity is poor (simulated in demo with env flag)  
**Model:** `gemma-2-9b-it` via Vertex AI  

```python
class ForecastOutbreakAgent(BaseAgent):
    
    async def get_model(self) -> Any:
        """Return Gemini or Gemma based on connectivity."""
        if settings.USE_GEMMA_FALLBACK or not await self.check_connectivity():
            logger.info("Using Gemma 2 fallback (offline mode)")
            return self.gemma_client   # Vertex AI Gemma
        return self.gemini_client      # Gemini 1.5 Flash
```

In demo: toggle `USE_GEMMA_FALLBACK=true` to show Gemma running. This earns +0.2 bonus points and demonstrates edge computing awareness.
