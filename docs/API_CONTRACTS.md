# AUSHADHI — API Contracts

> Base URL (local): http://localhost:8000
> Base URL (prod): https://aushadhi-api-[hash]-uc.a.run.app
> Auth: `X-API-Key: <AUSHADHI_API_KEY>` on every request
> Format: application/json | Timestamps: ISO 8601 UTC

---

## ENDPOINTS

### GET /health — No auth required
```json
{ "status": "healthy", "version": "1.0.0",
  "services": { "firestore": "connected", "pubsub": "connected", "gemini": "connected" } }
```

### GET /api/v1/metrics?district=East+Godavari
```json
{
  "centers_monitored": 8, "critical_stockouts": 6, "active_outbreak_alerts": 1,
  "pending_purchase_orders": 3, "avg_data_quality_score": 0.87,
  "total_pos_generated_today": 4, "total_pos_value_inr": 18450,
  "pipeline_last_run": "2026-08-20T08:00:00Z",
  "by_district": { "East Godavari": {...}, "Krishna": {...} }
}
```

### GET /api/v1/health-centers?district=&status=CRITICAL
Returns: `PaginatedResponse<HealthCenter>`

### GET /api/v1/health-centers/{center_id}
Returns: Full `HealthCenter` object

### GET /api/v1/inventory?center_id=&urgency=CRITICAL&medicine_id=
Returns: `PaginatedResponse<InventoryItem>`

### GET /api/v1/inventory/{center_id}/{medicine_id}
Returns: Full `InventoryItem` with 14-day consumption history

### POST /api/v1/consumption — Log daily consumption
```json
Request: { "center_id": "phc_razole_001", "medicine_id": "med_ors_001",
           "opening_stock": 145, "received_stock": 0, "closing_stock": 100,
           "report_date": "2026-08-20", "reported_by": "ASHA Lakshmi" }
Response 202: { "record_id": "...", "validated": true, "quality_score": 0.95 }
```

### GET /api/v1/outbreaks?status=ACTIVE&district=
Returns: `PaginatedResponse<OutbreakAlert>`

### PATCH /api/v1/outbreaks/{id}/acknowledge
```json
Request: { "acknowledged_by": "Dr. Venkateswara Rao" }
Response 200: { "id": "...", "status": "UNDER_RESPONSE", "acknowledged_by": "..." }
```

### PATCH /api/v1/outbreaks/{id}/resolve
```json
Request: { "resolution_notes": "Outbreak contained. Cholera confirmed in 2 cases." }
Response 200: { "id": "...", "status": "RESOLVED", "resolved_at": "..." }
```

### GET /api/v1/purchase-orders?status=PENDING_APPROVAL&priority=CRITICAL
Returns: `PaginatedResponse<PurchaseOrder>`

### PATCH /api/v1/purchase-orders/{id}/approve
```json
Request: { "approved_by": "District Health Officer" }
Response 200: { "po_number": "AUSD-...", "status": "APPROVED" }
```

### GET /api/v1/agents/status
```json
{
  "agents": [
    { "name": "SENTINEL", "status": "HEALTHY", "last_run": "...", "runs_today": 16, "avg_duration_ms": 1240 },
    { "name": "DQMS", "status": "HEALTHY", "records_validated_today": 128, "rejection_rate": 0.03 },
    { "name": "FORECAST", "status": "HEALTHY", "gemini_calls_today": 24, "avg_confidence": 0.86 },
    { "name": "PROCUREMENT", "status": "HEALTHY", "pos_generated_today": 4 },
    { "name": "ALERT", "status": "HEALTHY", "alerts_sent_today": 7 }
  ]
}
```

### GET /api/v1/agent-logs?agent_name=FORECAST&limit=50
Returns: `PaginatedResponse<AgentLog>`

### GET /api/v1/stream — SSE endpoint
Emits: `sentinel_cycle_started`, `inventory_updated`, `outbreak_detected`,
       `purchase_order_created`, `agent_step`, `pipeline_complete`, `heartbeat`

### POST /api/v1/internal/run-sentinel — Manually trigger pipeline
```json
Response 202: { "message": "Sentinel cycle started", "cycle_id": "cycle_abc123" }
```

### POST /api/v1/internal/simulate-outbreak — Demo trigger
```json
Response 202: { "message": "Outbreak scenario loaded for Razole mandal" }
```

### GET /api/v1/warehouses
Returns: List of warehouses with stock availability
