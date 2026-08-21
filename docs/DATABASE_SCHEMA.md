# AUSHADHI — Database Schema (Firestore)

> All collections in Firestore Native Mode, us-central1
> All timestamps: ISO 8601 UTC strings

---

## COLLECTION: `health_centers`
Document ID: Static (e.g., `phc_razole_001`)

```typescript
interface HealthCenter {
  id: string;
  name: string;                    // "PHC Razole"
  type: "SC" | "PHC" | "CHC" | "DH";  // Sub-Centre, Primary, Community, District
  district: string;                // "East Godavari"
  subdistrict: string;             // "Razole"
  address: string;
  location: { lat: number; lng: number; };
  catchment_population: number;
  medical_officer: string;         // Name of doctor in charge
  contact_phone: string;
  contact_email: string;
  
  status: {
    last_checked: string;          // When Sentinel last polled
    overall_stock_status: "CRITICAL" | "LOW" | "MODERATE" | "GOOD";
    critical_items_count: number;
    low_items_count: number;
    data_quality_score: number;    // 0.0 - 1.0 (from DQMS agent)
    last_report_date: string;      // Last consumption report date
    reporting_status: "ON_TIME" | "DELAYED" | "MISSING";
  };
  
  nearest_warehouse_id: string;
  nearest_warehouse_distance_km: number;
  created_at: string;
  updated_at: string;
}
```

---

## COLLECTION: `medicines`
Document ID: Static (e.g., `med_ors_001`)

```typescript
interface Medicine {
  id: string;
  name: string;                    // "ORS Packets (WHO Formula)"
  generic_name: string;            // "Oral Rehydration Salt"
  category: "ANTIBIOTIC" | "ANALGESIC" | "ORS_ELECTROLYTE" | "ANTIMALARIA" | 
            "IV_FLUID" | "VITAMIN" | "ANTIPARASITIC" | "VACCINE" | "OTHER";
  unit: string;                    // "packets", "tablets", "vials", "litres"
  essential: boolean;              // Is this on Essential Medicines List?
  
  // Outbreak indicators — which diseases this medicine signals
  outbreak_indicators: {
    disease: string;
    significance: "PRIMARY" | "SECONDARY";
    baseline_ratio_threshold: number;  // Ratio above which it's significant
  }[];
  
  // Standard thresholds (can be overridden per health center)
  default_minimum_threshold_units: number;
  default_maximum_capacity_units: number;
  
  unit_cost_inr: number;
  created_at: string;
}
```

---

## COLLECTION: `inventory`
Document ID: Auto-generated | Subcollection: `health_centers/{id}/inventory/{medicine_id}`
**Use subcollection for efficient per-center queries**

```typescript
interface InventoryItem {
  center_id: string;
  medicine_id: string;
  medicine_name: string;           // Denormalized for query efficiency
  
  // Stock levels
  current_stock: number;
  minimum_threshold: number;
  maximum_capacity: number;
  stock_percentage: number;        // current / maximum * 100
  
  // Derived fields (updated by Sentinel Agent)
  urgency: "CRITICAL" | "LOW" | "MONITOR" | "OK";
  days_until_stockout: number | null;  // null if OK
  
  // Consumption tracking
  opening_stock_today: number;
  daily_consumption_today: number;
  seven_day_avg_consumption: number;
  thirty_day_avg_consumption: number;
  consumption_ratio: number;       // today / 7d_avg
  anomaly_flag: boolean;
  anomaly_ratio: number | null;
  
  // Pending orders
  pending_order_quantity: number;  // Sum of PENDING purchase orders
  expected_stock_date: string | null;  // When next order arrives
  
  // Metadata
  last_updated: string;
  last_reported_by: string;        // ASHA worker / ANM name
  updated_at: string;
}
```

---

## COLLECTION: `consumption_records`
Document ID: Auto-generated

```typescript
interface ConsumptionRecord {
  id: string;
  center_id: string;
  medicine_id: string;
  
  report_date: string;             // "2026-08-20" (date only, not timestamp)
  
  opening_stock: number;
  received_stock: number;          // New stock received this day
  closing_stock: number;
  daily_consumption: number;       // opening + received - closing
  
  // DQMS fields
  is_valid: boolean;
  validation_errors: string[];
  validation_warnings: string[];
  quality_score: number;
  
  reported_by: string;             // Name of person who filed report
  report_source: "MANUAL_API" | "MOBILE_APP" | "SIMULATED";
  
  created_at: string;
}
```

---

## COLLECTION: `outbreak_alerts`
Document ID: Auto-generated

```typescript
interface OutbreakAlert {
  id: string;
  
  // From Gemini Outbreak Detection
  outbreak_detected: boolean;
  risk_level: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" | "NONE";
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
  outbreak_summary: string;        // The one-sentence Gemini summary
  differential_diagnosis: string;
  recommended_actions: string[];
  recommended_surveillance_actions: string[];
  gemini_full_response: string;    // Full Gemini JSON for audit
  
  // Status tracking
  status: "ACTIVE" | "UNDER_RESPONSE" | "RESOLVED" | "FALSE_POSITIVE";
  acknowledged_by: string | null;
  acknowledged_at: string | null;
  resolved_at: string | null;
  resolution_notes: string | null;
  
  // Linked purchase orders (emergency procurement)
  linked_po_ids: string[];
  
  district: string;
  created_at: string;
  updated_at: string;
}
```

---

## COLLECTION: `purchase_orders`
Document ID: Auto-generated (PO number stored as field)

```typescript
interface PurchaseOrder {
  id: string;
  po_number: string;               // "AUSD-20260820-0047"
  
  health_center_id: string;
  health_center_name: string;
  district: string;
  
  warehouse_id: string;
  warehouse_name: string;
  warehouse_distance_km: number;
  estimated_delivery_hours: number;
  
  priority: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";
  
  line_items: {
    medicine_id: string;
    medicine_name: string;
    requested_quantity: number;
    unit: string;
    unit_cost_inr: number;
    total_cost_inr: number;
    urgency: string;
    days_until_stockout: number;
  }[];
  
  total_cost_inr: number;
  
  status: "PENDING_APPROVAL" | "APPROVED" | "DISPATCHED" | "DELIVERED" | "CANCELLED";
  
  outbreak_linked: boolean;
  outbreak_alert_id: string | null;
  
  // Approval tracking
  approval_required: boolean;
  approved_by: string | null;
  approved_at: string | null;
  dispatched_at: string | null;
  delivered_at: string | null;
  
  generated_by: "AUSHADHI_PROCUREMENT_AGENT";
  created_at: string;
  updated_at: string;
}
```

---

## COLLECTION: `agent_logs`
Document ID: Auto-generated (same as SANJEEVANI pattern)

```typescript
interface AgentLog {
  id: string;
  center_id: string | null;        // Null for district-wide operations
  agent_name: "SENTINEL" | "DQMS" | "FORECAST" | "PROCUREMENT" | "ALERT";
  action: string;
  status: "STARTED" | "COMPLETED" | "FAILED" | "RETRYING";
  input: Record<string, any>;
  output: Record<string, any>;
  duration_ms: number;
  gemini_prompt?: string;
  gemini_response?: string;
  error?: { message: string; retry_count: number; };
  created_at: string;
  completed_at: string | null;
}
```

---

## COLLECTION: `warehouses`
Document ID: Static (e.g., `wh_rajahmundry_001`)

```typescript
interface Warehouse {
  id: string;
  name: string;                    // "District Medical Stores, Rajahmundry"
  district: string;
  location: { lat: number; lng: number; address: string; };
  contact: { phone: string; email: string; };
  
  // Current stock (simplified for hackathon)
  available_medicines: {
    medicine_id: string;
    medicine_name: string;
    available_quantity: number;
  }[];
  
  operating_hours: string;         // "Mon-Sat 8AM-6PM"
  created_at: string;
  updated_at: string;
}
```

---

## FIRESTORE INDEXES (firestore.indexes.json)

```json
{
  "indexes": [
    {
      "collectionGroup": "inventory",
      "fields": [
        { "fieldPath": "center_id", "order": "ASCENDING" },
        { "fieldPath": "urgency", "order": "ASCENDING" }
      ]
    },
    {
      "collectionGroup": "inventory",
      "fields": [
        { "fieldPath": "urgency", "order": "ASCENDING" },
        { "fieldPath": "updated_at", "order": "DESCENDING" }
      ]
    },
    {
      "collectionGroup": "consumption_records",
      "fields": [
        { "fieldPath": "center_id", "order": "ASCENDING" },
        { "fieldPath": "medicine_id", "order": "ASCENDING" },
        { "fieldPath": "report_date", "order": "DESCENDING" }
      ]
    },
    {
      "collectionGroup": "outbreak_alerts",
      "fields": [
        { "fieldPath": "status", "order": "ASCENDING" },
        { "fieldPath": "created_at", "order": "DESCENDING" }
      ]
    },
    {
      "collectionGroup": "purchase_orders",
      "fields": [
        { "fieldPath": "status", "order": "ASCENDING" },
        { "fieldPath": "priority", "order": "ASCENDING" },
        { "fieldPath": "created_at", "order": "DESCENDING" }
      ]
    },
    {
      "collectionGroup": "agent_logs",
      "fields": [
        { "fieldPath": "agent_name", "order": "ASCENDING" },
        { "fieldPath": "created_at", "order": "DESCENDING" }
      ]
    }
  ]
}
```
