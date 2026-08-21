# AUSHADHI — Complete File Structure
### Every file that must exist. Platform responsible is noted.

```
aushadhi/
│
├── README.md                          [Submit to GitHub]
├── DEMO_SCRIPT.md                     [Reference during recording]
├── BUILD_ORDER.md                     [Read first — then follow]
├── LOVABLE_START_PROMPT.md           [Copy to Lovable message 1]
├── PLAN_OF_APPROACH.md               [11-day schedule]
├── .env.example                       [Template — never commit .env]
├── .gitignore                         [See below]
│
├── docs/
│   ├── PRD.md                         [Product requirements]
│   ├── ARCHITECTURE.md               [System design]
│   ├── TECHNICAL_STACK.md            [All versions]
│   ├── AGENTS_SPEC.md                [CRITICAL — exact Gemini prompts]
│   ├── DATABASE_SCHEMA.md            [All Firestore schemas]
│   ├── API_CONTRACTS.md              [All endpoints]
│   ├── FRONTEND_SPEC.md              [Lovable page-by-page guide]
│   ├── PIPELINE.md                   [Event flow]
│   └── DEPLOYMENT.md                 [GCP step-by-step]
│
├── scripts/                           [Run these manually]
│   ├── test_gemini_outbreak.py        [RUN THIS FIRST — Day 3]
│   ├── seed_firestore.py             [Run once — Day 1]
│   ├── simulate_consumption.py       [Generate demo data]
│   └── teardown.sh                   [Scale to zero — run every night]
│
├── backend/                           [Claude Code + Antigravity SDK]
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   ├── .env.example
│   │
│   ├── main.py                        FastAPI app + startup events
│   ├── config.py                      All settings via pydantic-settings
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── router.py                  Mount all route groups here
│   │   ├── dependencies.py            Shared FastAPI depends()
│   │   │
│   │   ├── middleware/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py                X-API-Key validation
│   │   │   └── cors.py                CORS config
│   │   │
│   │   └── routes/
│   │       ├── __init__.py
│   │       ├── health_centers.py      GET /api/v1/health-centers
│   │       ├── inventory.py           GET /api/v1/inventory
│   │       ├── outbreaks.py           GET+PATCH /api/v1/outbreaks
│   │       ├── purchase_orders.py     GET+PATCH /api/v1/purchase-orders
│   │       ├── agents.py              GET /api/v1/agents/status
│   │       ├── metrics.py             GET /api/v1/metrics
│   │       ├── stream.py              GET /api/v1/stream (SSE)
│   │       └── internal.py            POST /api/v1/internal/* (demo triggers)
│   │
│   ├── agents/                        [Build in this order]
│   │   ├── __init__.py
│   │   ├── base_agent.py              Abstract base: run(), log_start(), log_complete()
│   │   ├── sentinel_agent.py          Polls Firestore, publishes to aushadhi-sentinel-alerts
│   │   ├── dqms_agent.py             Validates consumption data, publishes to validated-data
│   │   ├── forecast_agent.py          Gemini calls (prompts from AGENTS_SPEC.md), publishes to forecast-complete
│   │   ├── procurement_agent.py       Haversine routing, generates PO, publishes to procured
│   │   ├── alert_agent.py            Notification templates, logs to Cloud Logging
│   │   └── orchestrator.py            Manages all 4 Pub/Sub subscriptions concurrently
│   │
│   ├── models/                        [Build before services]
│   │   ├── __init__.py
│   │   ├── health_center.py
│   │   ├── inventory.py
│   │   ├── outbreak.py
│   │   ├── purchase_order.py
│   │   └── agent_log.py
│   │
│   ├── services/                      [Build before agents]
│   │   ├── __init__.py
│   │   ├── firestore_service.py       All Firestore reads/writes
│   │   ├── pubsub_service.py          publish() and subscribe()
│   │   ├── gemini_service.py          Wraps Gemini API calls (SAME prompts as test script)
│   │   ├── geocoding_service.py       haversine() distance calculation
│   │   └── notification_service.py    Log-based notifications for demo
│   │
│   └── utils/
│       ├── __init__.py
│       ├── logger.py                  structlog setup
│       ├── retry.py                   @retry decorator with exponential backoff
│       └── validators.py              DQMS validation rules
│
├── frontend/                          [Lovable builds this entire directory]
│   ├── package.json
│   ├── tsconfig.json
│   ├── tsconfig.node.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   ├── postcss.config.js
│   ├── index.html
│   ├── .env.example
│   ├── .env.local                     [Never commit — has VITE_API_KEY]
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── vite-env.d.ts
│       ├── constants/
│       │   └── api.ts
│       ├── types/                     [All TypeScript interfaces]
│       │   ├── health-center.ts
│       │   ├── inventory.ts
│       │   ├── outbreak.ts
│       │   ├── purchase-order.ts
│       │   ├── agent.ts
│       │   └── api.ts
│       ├── api/                       [Axios calls — one file per resource]
│       │   ├── client.ts
│       │   ├── health-centers.ts
│       │   ├── inventory.ts
│       │   ├── outbreaks.ts
│       │   ├── purchase-orders.ts
│       │   ├── agents.ts
│       │   └── metrics.ts
│       ├── store/
│       │   ├── dashboardStore.ts
│       │   └── uiStore.ts
│       ├── hooks/
│       │   ├── useSSE.ts              [Real-time EventSource connection]
│       │   ├── useHealthCenters.ts
│       │   ├── useInventory.ts
│       │   ├── useOutbreaks.ts
│       │   ├── usePurchaseOrders.ts
│       │   ├── useAgents.ts
│       │   └── useMetrics.ts
│       ├── components/
│       │   ├── layout/
│       │   │   ├── AppLayout.tsx      [Calls useSSE — runs on all pages]
│       │   │   ├── Sidebar.tsx
│       │   │   └── TopBar.tsx
│       │   ├── ui/                    [shadcn auto-generated]
│       │   └── shared/
│       │       ├── StockStatusBadge.tsx
│       │       ├── RiskLevelBadge.tsx
│       │       ├── AgentBadge.tsx
│       │       ├── PulsingDot.tsx
│       │       ├── LoadingSpinner.tsx
│       │       ├── ErrorState.tsx
│       │       └── EmptyState.tsx
│       └── pages/
│           ├── DashboardPage.tsx
│           ├── InventoryPage.tsx
│           ├── OutbreaksPage.tsx
│           ├── PurchaseOrdersPage.tsx
│           ├── PipelinePage.tsx
│           └── SettingsPage.tsx
│
├── infrastructure/
│   ├── cloudbuild.yaml
│   ├── cloudrun-api.yaml
│   ├── cloudrun-agents.yaml
│   ├── firestore.indexes.json
│   └── pubsub-topics.sh
│
└── architecture/
    ├── aushadhi-architecture.png      [For hackathon submission]
    └── aushadhi-architecture.drawio   [Source file]
```

---

## .gitignore (copy this exactly)

```
# Environment
.env
.env.local
.env.production
*.env

# Python
__pycache__/
*.py[cod]
*$py.class
.pytest_cache/
.mypy_cache/
*.egg-info/
dist/
build/
venv/
.venv/

# Node / Frontend
node_modules/
frontend/dist/
frontend/.env.local

# GCP credentials (NEVER commit these)
*service-account*.json
*credentials*.json
application_default_credentials.json

# IDE
.vscode/
.idea/
*.swp

# OS
.DS_Store
Thumbs.db

# Logs
*.log
```
