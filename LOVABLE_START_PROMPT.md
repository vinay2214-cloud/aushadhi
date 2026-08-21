# AUSHADHI — Perfect Lovable Starting Prompt
### Copy this EXACTLY as your first Lovable message. Do not change anything.
### This sets the entire foundation. Everything built after depends on this being right.

---

## HOW TO USE THIS FILE

1. Open Lovable → New Project → Name: "AUSHADHI"
2. Copy the prompt below (between the === markers) as your VERY FIRST message
3. Wait for Lovable to generate the foundation
4. VERIFY these exist before sending any more messages:
   - `src/api/client.ts` (Axios with X-API-Key interceptor)
   - `src/types/` folder with all interfaces
   - All 6 routes defined in App.tsx
   - Dark theme (background slate-950) applied
   - `src/hooks/useSSE.ts` exists
5. Then send the Dashboard page prompt from FRONTEND_SPEC.md

---

## ═══════════════════ COPY START ═══════════════════

Create a React TypeScript web application called **AUSHADHI** — an autonomous medicine supply intelligence system for rural healthcare in India.

## Project Setup

**Package manager:** npm
**Framework:** React 18 + TypeScript + Vite
**Styling:** Tailwind CSS + shadcn/ui (dark mode only)
**State:** TanStack Query (server state) + Zustand (client state)
**Routing:** React Router v6
**HTTP:** Axios
**Charts:** Recharts
**Maps:** React Leaflet + leaflet
**Dates:** date-fns
**Notifications:** react-hot-toast
**Icons:** lucide-react

Install these exact packages:
```
react react-dom react-router-dom
@tanstack/react-query axios zustand
recharts react-leaflet leaflet @types/leaflet
date-fns react-hot-toast lucide-react
tailwindcss postcss autoprefixer
@tailwindcss/forms
class-variance-authority clsx tailwind-merge
```

## Design System (STRICT — do not deviate)

- Background: `bg-slate-950` (all pages)
- Cards: `bg-slate-900 border border-slate-800/50 rounded-xl`
- Primary accent: `emerald-500` (buttons, active states, good indicators)
- Danger/Critical: `red-500`
- Warning/Low stock: `amber-500`
- Outbreak alerts: `orange-600`
- Info/Forecast: `purple-500`
- Text primary: `text-slate-100`
- Text secondary: `text-slate-400`
- Text muted: `text-slate-500`
- Sidebar: `bg-slate-900 w-60 border-r border-slate-800`
- Active sidebar item: `bg-emerald-500/10 text-emerald-400 border-l-2 border-emerald-500`
- NO light mode. NO mode toggle. Dark only.

## File Structure to Create

```
src/
├── main.tsx
├── App.tsx
├── vite-env.d.ts
├── constants/
│   └── api.ts          ← API base URL + all endpoint paths
├── types/
│   ├── health-center.ts
│   ├── inventory.ts
│   ├── outbreak.ts
│   ├── purchase-order.ts
│   ├── agent.ts
│   └── api.ts
├── api/
│   ├── client.ts       ← Axios instance with X-API-Key interceptor
│   ├── health-centers.ts
│   ├── inventory.ts
│   ├── outbreaks.ts
│   ├── purchase-orders.ts
│   ├── agents.ts
│   └── metrics.ts
├── store/
│   ├── dashboardStore.ts
│   └── uiStore.ts
├── hooks/
│   ├── useSSE.ts       ← Server-Sent Events hook
│   ├── useHealthCenters.ts
│   ├── useInventory.ts
│   ├── useOutbreaks.ts
│   ├── usePurchaseOrders.ts
│   ├── useAgents.ts
│   └── useMetrics.ts
├── components/
│   ├── layout/
│   │   ├── AppLayout.tsx
│   │   ├── Sidebar.tsx
│   │   └── TopBar.tsx
│   ├── ui/             ← shadcn components
│   └── shared/
│       ├── StockStatusBadge.tsx
│       ├── RiskLevelBadge.tsx
│       ├── AgentBadge.tsx
│       ├── PulsingDot.tsx
│       ├── LoadingSpinner.tsx
│       ├── ErrorState.tsx
│       └── EmptyState.tsx
└── pages/
    ├── DashboardPage.tsx
    ├── InventoryPage.tsx
    ├── OutbreaksPage.tsx
    ├── PurchaseOrdersPage.tsx
    ├── PipelinePage.tsx
    └── SettingsPage.tsx
```

## src/constants/api.ts (create exactly this)

```typescript
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
export const API_KEY = import.meta.env.VITE_API_KEY || '';

export const ENDPOINTS = {
  health: '/health',
  metrics: '/api/v1/metrics',
  healthCenters: '/api/v1/health-centers',
  inventory: '/api/v1/inventory',
  outbreaks: '/api/v1/outbreaks',
  purchaseOrders: '/api/v1/purchase-orders',
  agents: '/api/v1/agents/status',
  agentLogs: '/api/v1/agent-logs',
  stream: '/api/v1/stream',
  runSentinel: '/api/v1/internal/run-sentinel',
  simulateOutbreak: '/api/v1/internal/simulate-outbreak',
};
```

## src/api/client.ts (create exactly this)

```typescript
import axios from 'axios';
import { API_BASE_URL, API_KEY } from '../constants/api';

const client = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
});

client.interceptors.request.use((config) => {
  config.headers['X-API-Key'] = API_KEY;
  return config;
});

client.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error.response?.status, error.response?.data);
    return Promise.reject(error);
  }
);

export default client;
```

## src/hooks/useSSE.ts (create exactly this)

```typescript
import { useEffect, useRef } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import { API_BASE_URL, API_KEY } from '../constants/api';

export function useSSE() {
  const queryClient = useQueryClient();
  const sourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    function connect() {
      const url = `${API_BASE_URL}/api/v1/stream?api_key=${encodeURIComponent(API_KEY)}`;
      const source = new EventSource(url);
      sourceRef.current = source;

      source.addEventListener('inventory_updated', () => {
        queryClient.invalidateQueries({ queryKey: ['inventory'] });
        queryClient.invalidateQueries({ queryKey: ['health-centers'] });
      });

      source.addEventListener('outbreak_detected', (e) => {
        const data = JSON.parse(e.data);
        toast.custom(() => (
          <div className="bg-orange-900 border border-orange-600 rounded-xl p-4 text-orange-100 max-w-sm">
            <div className="font-semibold">🦠 Outbreak Alert — {data.risk_level}</div>
            <div className="text-sm mt-1">{data.outbreak_summary}</div>
          </div>
        ), { duration: 8000 });
        queryClient.invalidateQueries({ queryKey: ['outbreaks'] });
        queryClient.invalidateQueries({ queryKey: ['metrics'] });
      });

      source.addEventListener('purchase_order_created', (e) => {
        const data = JSON.parse(e.data);
        toast.success(`PO ${data.po_number} created — ${data.health_center_name}`, { duration: 5000 });
        queryClient.invalidateQueries({ queryKey: ['purchase-orders'] });
      });

      source.addEventListener('agent_step', () => {
        queryClient.invalidateQueries({ queryKey: ['agent-logs'] });
      });

      source.addEventListener('pipeline_complete', (e) => {
        const data = JSON.parse(e.data);
        toast.success(`Pipeline complete — ${data.centers_processed} centers processed`, { duration: 4000 });
        queryClient.invalidateQueries({ queryKey: ['metrics'] });
      });

      source.addEventListener('heartbeat', () => {
        // Keep-alive — no action needed
      });

      source.onerror = () => {
        source.close();
        setTimeout(connect, 3000);
      };
    }

    connect();
    return () => sourceRef.current?.close();
  }, [queryClient]);
}
```

## All TypeScript Types

Create `src/types/health-center.ts`:
```typescript
export type StockStatus = "CRITICAL" | "LOW" | "MODERATE" | "GOOD";
export type ReportingStatus = "ON_TIME" | "DELAYED" | "MISSING";
export type CenterType = "SC" | "PHC" | "CHC" | "DH";

export interface HealthCenter {
  id: string;
  name: string;
  type: CenterType;
  district: string;
  subdistrict: string;
  location: { lat: number; lng: number; };
  catchment_population: number;
  medical_officer: string;
  contact_phone: string;
  nearest_warehouse_distance_km: number;
  status: {
    last_checked: string;
    overall_stock_status: StockStatus;
    critical_items_count: number;
    low_items_count: number;
    data_quality_score: number;
    last_report_date: string;
    reporting_status: ReportingStatus;
  };
}
```

Create `src/types/inventory.ts`:
```typescript
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
```

Create `src/types/outbreak.ts`:
```typescript
export type RiskLevel = "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" | "NONE";
export type OutbreakStatus = "ACTIVE" | "UNDER_RESPONSE" | "RESOLVED" | "FALSE_POSITIVE";
export interface OutbreakAlert {
  id: string;
  outbreak_detected: boolean;
  risk_level: RiskLevel;
  disease_indicators: string[];
  affected_center_ids: string[];
  geographic_cluster: string;
  key_evidence: Array<{
    medicine: string;
    normal_daily_consumption: number;
    current_daily_consumption: number;
    ratio: number;
    significance: "HIGH" | "MEDIUM" | "LOW";
  }>;
  confidence: number;
  outbreak_summary: string;
  recommended_actions: string[];
  status: OutbreakStatus;
  acknowledged_by: string | null;
  linked_po_ids: string[];
  district: string;
  created_at: string;
}
```

Create `src/types/purchase-order.ts`:
```typescript
export type POStatus = "PENDING_APPROVAL" | "APPROVED" | "DISPATCHED" | "DELIVERED" | "CANCELLED";
export type POPriority = "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";
export interface PurchaseOrder {
  id: string;
  po_number: string;
  health_center_name: string;
  district: string;
  warehouse_name: string;
  warehouse_distance_km: number;
  estimated_delivery_hours: number;
  priority: POPriority;
  line_items: Array<{
    medicine_name: string;
    requested_quantity: number;
    unit: string;
    total_cost_inr: number;
    days_until_stockout: number;
  }>;
  total_cost_inr: number;
  status: POStatus;
  outbreak_linked: boolean;
  created_at: string;
}
```

Create `src/types/agent.ts`:
```typescript
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
export interface AgentStatus {
  name: AgentName;
  status: "HEALTHY" | "DEGRADED" | "DOWN";
  last_run: string | null;
  runs_today: number;
  avg_duration_ms: number | null;
}
```

Create `src/types/api.ts`:
```typescript
export interface PaginatedResponse<T> {
  data: T[];
  total: number;
  limit: number;
  offset: number;
  has_more: boolean;
}
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

## Routing (App.tsx)

```
/                → DashboardPage
/inventory       → InventoryPage
/outbreaks       → OutbreaksPage
/orders          → PurchaseOrdersPage
/pipeline        → PipelinePage
/settings        → SettingsPage
```

All routes wrapped in `AppLayout` (sidebar + topbar).

## Sidebar Navigation Items

```
💊  /            Dashboard
📦  /inventory   Inventory
🦠  /outbreaks   Outbreaks
📋  /orders      Purchase Orders
⚙️  /pipeline    Pipeline
🔧  /settings    Settings
```

Bottom of sidebar:
- "AUSHADHI" in emerald-500 font-bold text
- "Powered by Gemini + Google ADK" in slate-600 text-xs

## Shared Components to Create

```
StockStatusBadge({ status }):
  CRITICAL → bg-red-500/20 text-red-400 border border-red-500/30
  LOW → bg-amber-500/20 text-amber-400 border border-amber-500/30
  MODERATE → bg-blue-500/20 text-blue-400 border border-blue-500/30
  GOOD → bg-emerald-500/20 text-emerald-400 border border-emerald-500/30

RiskLevelBadge({ level }):
  CRITICAL → bg-red-600 text-white
  HIGH → bg-orange-600 text-white
  MEDIUM → bg-amber-500 text-slate-900
  LOW → bg-blue-500 text-white
  NONE → bg-slate-600 text-slate-300

AgentBadge({ agent }):
  SENTINEL → bg-slate-700 text-slate-300
  DQMS → bg-blue-900 text-blue-300
  FORECAST → bg-purple-900 text-purple-300 (most important)
  PROCUREMENT → bg-emerald-900 text-emerald-300
  ALERT → bg-orange-900 text-orange-300

PulsingDot({ color }):
  Animated pulsing dot (green/red/amber/orange)
  Use for: live status indicators

IndianRupeeFormat(amount: number):
  Returns "₹1,750" using Indian number formatting
  Use toLocaleString('en-IN', { style: 'currency', currency: 'INR' })
```

## TanStack Query Keys (MUST be consistent)

```typescript
['metrics']
['health-centers', { district?, status? }]
['health-center', id]
['inventory', { center_id?, urgency?, medicine_id? }]
['outbreaks', { status? }]
['purchase-orders', { status?, priority? }]
['agents']
['agent-logs', { agent_name?, limit? }]
```

## Important Rules

1. NEVER create mock data anywhere. Every number comes from the API or shows loading skeleton.
2. NEVER use localStorage or sessionStorage.
3. ALL pages are dark theme. bg-slate-950 background everywhere.
4. ALL API calls go through `src/api/client.ts` — never use fetch directly.
5. Show `LoadingSpinner` while data is loading, `ErrorState` on error, `EmptyState` when empty.
6. Use `react-hot-toast` for all notifications. No alert() or confirm().
7. The SSE hook (useSSE) must be called in AppLayout so it runs on all pages.
8. Format all Indian currency as ₹X,XXX using Indian locale.
9. ALL timestamps display in local timezone using date-fns `formatDistanceToNow`.

Do not build any pages yet. Just the foundation described above.
Confirm when done by listing the files created.

## ═══════════════════ COPY END ═══════════════════

---

## AFTER LOVABLE CONFIRMS FOUNDATION

Check these before proceeding:

```bash
# In Lovable terminal or download the code locally
ls src/api/
# Should show: client.ts, health-centers.ts, inventory.ts, ...

ls src/types/
# Should show: health-center.ts, inventory.ts, outbreak.ts, ...

ls src/hooks/
# Should show: useSSE.ts, useHealthCenters.ts, ...
```

Then send the Dashboard page prompt from FRONTEND_SPEC.md.
