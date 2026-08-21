# AUSHADHI — Frontend Specification (Lovable Build Guide)

> Platform: Lovable | Budget: 300 credits | Stack: React + TypeScript + Tailwind + shadcn/ui
> Theme: Dark only | Accent: Emerald green (health theme, not red)

---

## LOVABLE MASTER PROMPT (Send this first — 1 message)

```
Build a React TypeScript application called AUSHADHI — an autonomous medicine supply 
intelligence dashboard for rural healthcare in India.

Tech stack:
- React 18 + TypeScript + Vite
- Tailwind CSS + shadcn/ui
- TanStack Query (react-query) for all data fetching
- Zustand for client state  
- React Router v6
- Axios with X-API-Key header injected on every request
- Recharts for all charts
- React Leaflet for maps
- date-fns for dates
- react-hot-toast for notifications
- lucide-react icons

Design system:
- Dark theme ONLY (background: slate-950)
- Cards: slate-900, border: slate-800/50
- Primary accent: emerald-500 (health/life)
- Critical/danger: red-500
- Warning: amber-500
- Outbreak alerts: orange-600
- Sidebar: slate-900, width 240px

Routes:
- / → DashboardPage
- /inventory → InventoryPage
- /outbreaks → OutbreaksPage
- /orders → PurchaseOrdersPage
- /pipeline → PipelinePage
- /reports → ReportsPage
- /settings → SettingsPage

Global setup:
1. Axios client: src/api/client.ts reads VITE_API_BASE_URL + VITE_API_KEY
2. Inject X-API-Key on every request via interceptor
3. TanStack Query provider wrapping entire app
4. Zustand stores: dashboardStore.ts, uiStore.ts
5. SSE hook: src/hooks/useSSE.ts (EventSource to VITE_API_BASE_URL/api/v1/stream)
6. All TypeScript types in src/types/

NEVER use mock data. All data comes from the API.
NEVER use localStorage.
Dark theme throughout — no light mode toggle.
```

---

## TYPESCRIPT TYPES (Send as second message)

```typescript
// src/types/health-center.ts
export type StockStatus = "CRITICAL" | "LOW" | "MODERATE" | "GOOD";
export type ReportingStatus = "ON_TIME" | "DELAYED" | "MISSING";

export interface HealthCenter {
  id: string;
  name: string;
  type: "SC" | "PHC" | "CHC" | "DH";
  district: string;
  subdistrict: string;
  location: { lat: number; lng: number; };
  catchment_population: number;
  medical_officer: string;
  contact_phone: string;
  status: {
    last_checked: string;
    overall_stock_status: StockStatus;
    critical_items_count: number;
    low_items_count: number;
    data_quality_score: number;
    last_report_date: string;
    reporting_status: ReportingStatus;
  };
  nearest_warehouse_distance_km: number;
}

// src/types/inventory.ts
export type InventoryUrgency = "CRITICAL" | "LOW" | "MONITOR" | "OK";

export interface InventoryItem {
  center_id: string;
  medicine_id: string;
  medicine_name: string;
  current_stock: number;
  minimum_threshold: number;
  maximum_capacity: number;
  stock_percentage: number;
  urgency: InventoryUrgency;
  days_until_stockout: number | null;
  daily_consumption_today: number;
  seven_day_avg_consumption: number;
  consumption_ratio: number;
  anomaly_flag: boolean;
  anomaly_ratio: number | null;
  pending_order_quantity: number;
  last_updated: string;
}

// src/types/outbreak.ts
export type RiskLevel = "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" | "NONE";
export type OutbreakStatus = "ACTIVE" | "UNDER_RESPONSE" | "RESOLVED" | "FALSE_POSITIVE";

export interface OutbreakAlert {
  id: string;
  outbreak_detected: boolean;
  risk_level: RiskLevel;
  disease_indicators: string[];
  affected_center_ids: string[];
  geographic_cluster: string;
  key_evidence: {
    medicine: string;
    normal_daily_consumption: number;
    current_daily_consumption: number;
    ratio: number;
    significance: "HIGH" | "MEDIUM" | "LOW";
  }[];
  confidence: number;
  outbreak_summary: string;
  recommended_actions: string[];
  status: OutbreakStatus;
  acknowledged_by: string | null;
  linked_po_ids: string[];
  district: string;
  created_at: string;
}

// src/types/purchase-order.ts
export type POStatus = "PENDING_APPROVAL" | "APPROVED" | "DISPATCHED" | "DELIVERED" | "CANCELLED";
export type POPriority = "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";

export interface PurchaseOrder {
  id: string;
  po_number: string;
  health_center_id: string;
  health_center_name: string;
  district: string;
  warehouse_name: string;
  warehouse_distance_km: number;
  estimated_delivery_hours: number;
  priority: POPriority;
  line_items: {
    medicine_name: string;
    requested_quantity: number;
    unit: string;
    total_cost_inr: number;
    urgency: string;
    days_until_stockout: number;
  }[];
  total_cost_inr: number;
  status: POStatus;
  outbreak_linked: boolean;
  created_at: string;
}

// src/types/agent.ts
export type AgentName = "SENTINEL" | "DQMS" | "FORECAST" | "PROCUREMENT" | "ALERT";
export interface AgentLog {
  id: string;
  center_id: string | null;
  agent_name: AgentName;
  action: string;
  status: "STARTED" | "COMPLETED" | "FAILED" | "RETRYING";
  duration_ms: number | null;
  key_output: string;
  created_at: string;
}

// src/types/metrics.ts
export interface DashboardMetrics {
  centers_monitored: number;
  critical_stockouts: number;
  active_outbreak_alerts: number;
  pending_purchase_orders: number;
  avg_data_quality_score: number;
  total_pos_generated_today: number;
  total_pos_value_inr: number;
  pipeline_last_run: string;
}
```

---

## PAGE 1: DASHBOARD (/) — 70 credits

```
Build the Dashboard page with these exact sections:

1. TOP METRICS ROW (5 MetricCards side by side):
   - "Critical Stockouts" → metrics.critical_stockouts — red if > 0
   - "Outbreak Alerts" → metrics.active_outbreak_alerts — orange if > 0
   - "Centers Monitored" → metrics.centers_monitored — emerald
   - "Pending Orders" → metrics.pending_purchase_orders — amber
   - "Data Quality" → metrics.avg_data_quality_score as "XX%" — blue

2. OUTBREAK ALERT BANNER (only when outbreak_alerts exist with status=ACTIVE):
   - Full-width banner, orange-600 border, amber background tint
   - Shows: risk level badge + disease indicators + affected area + outbreak_summary
   - "View Full Analysis" button → navigates to /outbreaks
   - Pulsing red dot animation to draw attention
   - Dismiss button (marks acknowledged in UI only)

3. TWO COLUMN LAYOUT:

   LEFT (60%) — HEALTH CENTERS:
   - Title "Health Centers" with filter pills: ALL | CRITICAL | LOW | GOOD
   - Each HealthCenterCard shows:
     * Center name + type badge (PHC/CHC/DH)
     * District + subdistrict
     * Overall stock status badge (CRITICAL=red, LOW=amber, MODERATE=blue, GOOD=emerald)
     * Critical items count if > 0 (red badge)
     * Data quality score as small bar
     * "Last checked" relative time
     * Anomaly flag icon (orange triangle) if any medicine has anomaly_flag=true
     * Click → expands to show top 3 critical/low medicines inline
   - Sort: CRITICAL first, then LOW, then GOOD
   - SSE: update cards when emergency_updated event received

   RIGHT (40%) — AGENT ACTIVITY FEED:
   - Title: "Agent Pipeline" with pulsing green dot
   - Last 30 agent log entries
   - Each entry: colored agent badge + action text + center name + time
   - Agent badge colors:
     * SENTINEL: slate-500
     * DQMS: blue-500
     * FORECAST: purple-500 (most important)
     * PROCUREMENT: emerald-500
     * ALERT: orange-500
   - Gemini calls show a small sparkle icon
   - New entries slide in from top (SSE: agent_step event)
   - "Run Pipeline Now" button at top → POST /api/v1/internal/run-sentinel

4. SIMULATE BUTTON (bottom right, fixed):
   - "Simulate Stockout" button with beaker icon
   - Opens SimulateModal with pre-filled East Godavari outbreak scenario
   - On confirm: calls POST /api/v1/internal/simulate-outbreak
```

---

## PAGE 2: INVENTORY (/inventory) — 50 credits

```
Build the Inventory page:

1. FILTER BAR:
   - District filter: ALL | East Godavari | Krishna
   - Urgency filter: ALL | CRITICAL | LOW | MONITOR | OK
   - Medicine filter: searchable dropdown of all medicines
   - Center filter: searchable dropdown of all centers

2. INVENTORY HEATMAP TABLE:
   - Rows: health centers
   - Columns: key medicines (ORS, Zinc, IV Saline, Paracetamol, Metronidazole, Chloroquine)
   - Each cell shows stock_percentage as colored circle:
     * 0-15%: red-500 filled circle (CRITICAL)
     * 15-30%: amber-500 (LOW)
     * 30-50%: blue-400 (MONITOR)
     * 50%+: emerald-500 (OK)
   - Hover on cell: tooltip showing current_stock, days_until_stockout, consumption_ratio
   - Anomaly cells have pulsing animation
   - Click row: navigate to center detail view

3. BELOW TABLE — CRITICAL ITEMS LIST:
   - Title "Items Requiring Immediate Action"
   - Table: Center | Medicine | Stock % | Days Left | Consumption Ratio | Anomaly | Action
   - Sorted by days_until_stockout ascending (most urgent first)
   - Anomaly flag shown as orange ⚠ with ratio value
   - "Create PO" button per row → opens CreatePOModal

4. DATA QUALITY SECTION:
   - Title "DQMS Data Quality Report"
   - Per-center quality score as horizontal bar (green > 0.85, amber 0.7-0.85, red < 0.7)
   - Shows: valid records, rejected records, warnings count
```

---

## PAGE 3: OUTBREAKS (/outbreaks) — 40 credits

```
Build the Outbreaks Intelligence page:

1. ACTIVE ALERTS SECTION:
   - Full-width cards, one per active outbreak_alert
   - Each card shows:
     * Risk level badge (large, prominent): CRITICAL=red, HIGH=orange, MEDIUM=amber
     * Confidence percentage with progress bar
     * Disease indicators as colored tags
     * outbreak_summary in large italic quote
     * Geographic cluster text
     * "Key Evidence" section — show key_evidence as small table:
       Medicine | Normal | Current | Ratio — ratio shown in red if > 2.0
     * Recommended actions as numbered list
     * Affected centers as linked tags
     * Linked purchase orders section
     * "Acknowledge" button → PATCH /api/v1/outbreaks/{id}/acknowledge
     * "Mark Resolved" button → PATCH /api/v1/outbreaks/{id}/resolve

2. MAP (below alerts):
   - React Leaflet map showing all health centers
   - CRITICAL centers: pulsing red markers
   - Outbreak-affected centers: orange markers with larger radius
   - Normal centers: emerald markers
   - Click marker: popup with center info + stock status

3. OUTBREAK HISTORY:
   - Table of past outbreaks (status = RESOLVED or FALSE_POSITIVE)
   - Columns: Date | Disease | Centers | Risk Level | Status | Resolution time
```

---

## PAGE 4: PURCHASE ORDERS (/orders) — 30 credits

```
Build the Purchase Orders page:

1. STATUS TABS: PENDING APPROVAL | APPROVED | DISPATCHED | DELIVERED | ALL

2. PO CARDS (one per order):
   - Header: PO number (monospace) + priority badge + status badge + created time
   - Health center name → warehouse name + distance
   - Line items table: Medicine | Quantity | Unit | Cost
   - Total cost (formatted in Indian rupees: ₹X,XXX)
   - Outbreak linked badge (orange) if outbreak_linked=true
   - Estimated delivery time
   - Action buttons based on status:
     * PENDING_APPROVAL: "Approve PO" (emerald) + "Reject" (red)
     * APPROVED: "Mark Dispatched"
     * DISPATCHED: "Mark Delivered"
   - On Approve: PATCH /api/v1/purchase-orders/{id}/approve
   - Show total value across all PENDING orders as summary stat at top

3. SUMMARY ROW (top):
   - Total pending (count + ₹ value)
   - Total approved
   - Total dispatched
   - Total delivered today
```

---

## PAGE 5: PIPELINE (/pipeline) — 25 credits

```
Build the Pipeline Activity page:

1. AGENT STATUS CARDS (5 cards, horizontal):
   - SENTINEL: shield icon, slate
   - DQMS: check-circle icon, blue — show "Data quality avg" 
   - FORECAST: brain icon, purple — show "Gemini calls today"
   - PROCUREMENT: package icon, emerald — show "POs generated"
   - ALERT: bell icon, orange — show "Alerts sent"
   - Each shows: status (HEALTHY/DEGRADED/DOWN), last run time, runs today

2. PIPELINE RUN HISTORY:
   - Each run shows as a timeline row:
     [SENTINEL] → [DQMS] → [FORECAST] → [PROCUREMENT] + [ALERT]
   - Each step: status icon + duration in ms
   - Expandable to show full agent log for that run
   - Gemini responses shown in purple quote blocks

3. REAL-TIME LOG (bottom, live feed):
   - SSE stream shows agent_step events
   - Color coded by agent name
```

---

## PAGE 6: SETTINGS (/settings) — 15 credits

```
Build Settings page:

1. CONNECTION STATUS:
   - API URL (read-only input + copy button)
   - Connection status: green/red dot
   - "Test Connection" → GET /health

2. DEMO CONTROLS:
   - "Run Full Pipeline Now" → POST /api/v1/internal/run-sentinel
   - "Simulate Razole Cholera Outbreak" → POST /api/v1/internal/simulate-outbreak
   - "Reset Demo Data" → POST /api/v1/internal/reset-demo (re-runs seed)
   - "Toggle Gemma Fallback" toggle → PATCH /api/v1/config (shows which model is active)

3. SYSTEM INFO:
   - Districts monitored, centers monitored, medicines tracked
   - Last pipeline run
   - Gemini model in use (Gemini 1.5 Flash / Gemma 2)
```

---

## SHARED COMPONENTS (Must exist)

```
StockStatusBadge: CRITICAL (red) | LOW (amber) | MODERATE (blue) | GOOD (emerald)
RiskLevelBadge: CRITICAL (red) | HIGH (orange) | MEDIUM (amber) | LOW (blue) | NONE (slate)
AgentBadge: color-coded per agent name
ConsumptionRatioDisplay: shows ratio as "3.8x" with color (red > 2, amber > 1.3, green ≤ 1.3)
DaysUntilStockout: shows "X days" in red if < 7, amber if < 14
DataQualityBar: colored horizontal bar 0-100%
PulsingDot: animated status indicator (green=OK, red=critical, amber=warning)
IndianRupee: formats number as "₹X,XXX" with Indian number formatting
TimeAgo: "3m ago", "2h ago" using date-fns
```

---

## SSE EVENTS THE FRONTEND HANDLES

```typescript
// Connect on mount: EventSource(`${VITE_API_BASE_URL}/api/v1/stream?api_key=${VITE_API_KEY}`)

source.addEventListener('sentinel_cycle_started', (e) => {
  // Show "Pipeline running..." indicator on dashboard
});

source.addEventListener('inventory_updated', (e) => {
  // data: { center_id, medicine_id, new_stock_percentage, urgency }
  queryClient.invalidateQueries({ queryKey: ['inventory'] });
});

source.addEventListener('outbreak_detected', (e) => {
  // data: { outbreak_id, risk_level, disease_indicators, outbreak_summary }
  toast.custom(...) // Show outbreak banner immediately
  queryClient.invalidateQueries({ queryKey: ['outbreaks'] });
});

source.addEventListener('purchase_order_created', (e) => {
  // data: { po_number, health_center_name, priority, total_cost_inr }
  toast.success(`PO ${data.po_number} generated for ${data.health_center_name}`);
  queryClient.invalidateQueries({ queryKey: ['purchase-orders'] });
});

source.addEventListener('agent_step', (e) => {
  // data: { agent_name, action, center_id, status, duration_ms }
  // Add to agent activity feed
});

source.addEventListener('pipeline_complete', (e) => {
  // data: { duration_seconds, centers_processed, alerts_generated, pos_created }
  toast.success(`Pipeline complete: ${data.centers_processed} centers processed`);
  queryClient.invalidateQueries({ queryKey: ['metrics'] });
});
```

---

## LOVABLE CREDIT ALLOCATION

| Page/Feature | Credits |
|-------------|---------|
| Master setup + types + API client | 30 |
| Dashboard (full, with SSE) | 70 |
| Inventory heatmap + quality | 50 |
| Outbreaks intelligence | 40 |
| Purchase orders | 30 |
| Pipeline activity | 25 |
| Settings | 15 |
| Bug fixes + polish | 40 |
| **TOTAL** | **300** |
