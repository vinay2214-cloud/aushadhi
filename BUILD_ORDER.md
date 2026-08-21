# AUSHADHI — Build Order & Platform Strategy
### Exactly what to build, in exactly what order, on exactly which platform

---

## THE RULE: Backend First. Always.

Do NOT open Lovable until Day 6. Here is why:

Lovable generates React components that call your API. If your API doesn't exist yet, Lovable has nothing real to connect to. You end up building a beautiful dashboard that shows `undefined` everywhere, then spending credits fixing that instead of building features. Build the backend until `GET /api/v1/outbreaks` returns real Gemini-generated outbreak data. THEN open Lovable.

---

## PLATFORM MAP

```
Day 1–2    GCP Console + gcloud CLI + Python (scripts only)
Day 3      Python standalone script (test_gemini_outbreak.py)
Day 3–5    Claude Code + Antigravity SDK (backend/)
Day 6–8    Lovable (frontend/) — connects to running backend
Day 9      gcloud CLI (deployment)
Day 10     draw.io (architecture diagram)
Day 11     OBS/Loom (demo video) + dev.to (article)
Day 12     Devpost (submission)
```

---

## PHASE 1: VALIDATE (Days 1–2, ~6 hours)

**Platform: Terminal + GCP Console**

### Step 1: GCP Project Setup
```bash
# Install gcloud if not done: https://cloud.google.com/sdk/docs/install
gcloud auth login
export PROJECT_ID="aushadhi-hackathon"
gcloud projects create $PROJECT_ID
gcloud config set project $PROJECT_ID

# Enable all APIs at once
gcloud services enable \
  run.googleapis.com \
  firestore.googleapis.com \
  pubsub.googleapis.com \
  cloudscheduler.googleapis.com \
  secretmanager.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  aiplatform.googleapis.com
```

### Step 2: Get Gemini API Key
1. Go to https://aistudio.google.com/app/apikey
2. Click "Create API key"
3. Copy the key — it starts with `AIzaSy`
4. Store it: `echo "GOOGLE_API_KEY=AIzaSy..." > .env`

### Step 3: Claim Google Cloud Credits
1. Go to the hackathon Resources tab
2. Fill credit form (DEADLINE: August 28, 12PM PT — do this NOW)

### Step 4: Create Firestore
```bash
gcloud firestore databases create \
  --database="(default)" \
  --location="us-central1" \
  --type="firestore-native"
```

### Step 5: Seed Initial Data
```bash
pip install google-cloud-firestore python-dotenv haversine
python3 scripts/seed_firestore.py
# Expected: 8 health centers, 10 medicines, 7 days consumption history seeded
```

**End of Phase 1 checkpoint:** Firestore has data. API key works.

---

## PHASE 2: VALIDATE GEMINI (Day 3 morning, 2–4 hours)

**Platform: Python standalone — NO backend framework needed**

### THE MOST IMPORTANT STEP IN THE ENTIRE PROJECT

```bash
pip install google-generativeai python-dotenv
python3 scripts/test_gemini_outbreak.py
```

**If output shows both ✅ PASSED:**
You have the foundation. Gemini understands the cholera outbreak scenario.
Proceed to Phase 3 immediately.

**If either test ❌ FAILS:**
DO NOT proceed. Fix the issue in the test script first.
The prompts in this test file are the exact same prompts used in `agents/forecast_agent.py`.
A failure here means the agent will fail in production.

---

## PHASE 3: BACKEND (Days 3–5, ~15 hours)

**Platform: Claude Code + Antigravity SDK**

### Build Order Within Backend (strict — each step depends on previous)

```
STEP 1: backend/config.py
        backend/utils/logger.py
        backend/utils/retry.py
        backend/main.py (FastAPI skeleton only — no routes yet)
        
        Test: uvicorn main:app --reload → GET /health returns 200
        
STEP 2: backend/models/*.py (all Pydantic models)
        → health_center.py, inventory.py, outbreak.py, purchase_order.py, agent_log.py
        
        Test: python3 -c "from models.outbreak import OutbreakAlert; print('OK')"
        
STEP 3: backend/services/firestore_service.py
        → All CRUD operations for all collections
        → Test each method individually before moving on
        
        Test: python3 -c "
        from services.firestore_service import FirestoreService
        fs = FirestoreService()
        centers = fs.get_all_health_centers()
        print(f'Found {len(centers)} health centers')
        "
        
STEP 4: backend/services/pubsub_service.py
        → publish() and subscribe() methods
        → Create Pub/Sub topics (run infrastructure/pubsub-topics.sh)
        
        Test: Publish one test message, confirm it appears in GCP Console

STEP 5: backend/services/gemini_service.py
        → Call Gemini with the EXACT prompts from test_gemini_outbreak.py
        → Parse JSON response
        → Return structured Python dict
        
        Test: python3 -c "
        from services.gemini_service import GeminiService
        g = GeminiService()
        result = g.detect_outbreak([...test_data...])
        print(result['risk_level'])
        "
        
STEP 6: backend/agents/base_agent.py
        backend/agents/sentinel_agent.py
        backend/agents/dqms_agent.py
        
        Test: python3 -c "
        from agents.sentinel_agent import SentinelAgent
        import asyncio
        asyncio.run(SentinelAgent().scan_all_centers())
        "
        
STEP 7: backend/agents/forecast_agent.py  ← THE HEART
        → Uses gemini_service.py for both forecast + outbreak calls
        → COPY THE PROMPTS EXACTLY from test_gemini_outbreak.py
        
        Test: Trigger sentinel → confirm forecast_agent fires → confirm Firestore 
              outbreak_alerts collection has a document with risk_level=HIGH
        
STEP 8: backend/agents/procurement_agent.py
        backend/agents/alert_agent.py
        backend/agents/orchestrator.py
        
        Test: Full end-to-end: POST /api/v1/internal/run-sentinel → watch terminal →
              confirm 5 agent steps logged → confirm purchase_order created in Firestore
              
STEP 9: backend/api/routes/*.py (all API routes)
        
        Test every route with curl:
        curl -H "X-API-Key: $KEY" http://localhost:8000/api/v1/inventory?urgency=CRITICAL
        curl -H "X-API-Key: $KEY" http://localhost:8000/api/v1/outbreaks
        curl -H "X-API-Key: $KEY" http://localhost:8000/api/v1/purchase-orders
        
STEP 10: backend/api/routes/stream.py (SSE)
        
        Test: curl -N "http://localhost:8000/api/v1/stream?api_key=$KEY"
              → You should see heartbeat events every 30s
              → Trigger pipeline → confirm SSE emits events
```

**End of Phase 3 checkpoint:**
- POST /api/v1/internal/run-sentinel → 5 agents fire → outbreak alert created
- GET /api/v1/outbreaks → returns outbreak with risk_level=HIGH, disease=CHOLERA
- GET /api/v1/purchase-orders → returns auto-generated PO for Razole
- SSE stream → emits events when pipeline runs
- ALL tests passing

---

## PHASE 4: FRONTEND WITH LOVABLE (Days 6–8, ~12 hours)

**Platform: Lovable (300 credits)**

### Before Opening Lovable
```bash
# Backend must be running on localhost:8000
# Test it manually:
curl -H "X-API-Key: your-key" http://localhost:8000/api/v1/metrics
# Should return real numbers, not empty/errors
```

### Lovable Session Structure (IMPORTANT — read before spending credits)

Each Lovable message costs credits. Use them efficiently:

```
Message 1:  Foundation setup (LOVABLE_START_PROMPT.md — the master prompt)
            → Do NOT request any pages yet
            → Just: routing, API client, types, layout, theme
            → After this: verify dark theme works, routes exist, API client exists

Message 2:  Dashboard page ONLY
            → Copy exact prompt from docs/FRONTEND_SPEC.md "PAGE 1"
            → After this: verify metrics load, health center cards show

Message 3:  Fix SSE connection
            → Copy useSSE hook from FRONTEND_SPEC.md exactly
            → Test: trigger pipeline, watch dashboard update live

Message 4:  Inventory page (heatmap)
Message 5:  Outbreaks page (the most important visual)
Message 6:  Purchase Orders page
Message 7:  Pipeline + Settings pages
Message 8+: Bug fixes (save ~40 credits for this)
```

### Connecting Lovable to Your Backend

In Lovable, set environment variable:
```
VITE_API_BASE_URL=http://localhost:8000
VITE_API_KEY=your-aushadhi-api-key
```

Lovable has a way to set env vars in project settings.
Test that data flows: trigger pipeline from dashboard → see real Gemini outbreak appear.

---

## PHASE 5: DEPLOYMENT (Day 9, ~4 hours)

**Platform: gcloud CLI**

Follow docs/DEPLOYMENT.md step by step.
Critical: Deploy backend BEFORE frontend (frontend needs backend URL).

Order:
1. Build + push Docker images to Artifact Registry
2. Deploy `aushadhi-api` Cloud Run service
3. Deploy `aushadhi-agents` Cloud Run service
4. Set up Cloud Scheduler
5. Seed production Firestore (run seed script against production)
6. Build frontend with production VITE_API_BASE_URL
7. Deploy `aushadhi-frontend` Cloud Run service
8. Test end-to-end on production URLs
9. Screenshot Cloud Run dashboard for demo video

---

## PHASE 6: DEMO + SUBMIT (Days 10–12)

Day 10: Architecture diagram (draw.io) + Practice DEMO_SCRIPT.md
Day 11: Record video + Write dev.to article + LinkedIn post
Day 12: Submit on Devpost before 5PM PT

---

## GIVING CONTEXT TO CLAUDE CODE

When starting Claude Code, give it these files in this order:

```
First message to Claude Code:
"I'm building AUSHADHI — autonomous medicine supply intelligence.
Here is the complete spec. Build the backend in Python FastAPI.
[paste FILE_STRUCTURE.md]
[paste docs/TECHNICAL_STACK.md — backend section only]
[paste docs/DATABASE_SCHEMA.md]

Start with: config.py, utils/logger.py, utils/retry.py, main.py skeleton.
Do not build any agents or routes yet."

Second message:
"Now build backend/models/*.py exactly matching these schemas:
[paste docs/DATABASE_SCHEMA.md — TypeScript interfaces section]"

Third message:
"Now build backend/services/firestore_service.py.
Methods needed: [list from API_CONTRACTS.md]"

... continue one component at a time
```

## GIVING CONTEXT TO ANTIGRAVITY SDK

When using Antigravity SDK for agent integration:

```
"I'm building 5 AI agents for AUSHADHI. Here is the agent specification:
[paste docs/AGENTS_SPEC.md]

The Gemini prompts are already validated via test_gemini_outbreak.py.
Build agents/forecast_agent.py first — it is the most critical agent.
Use the EXACT system prompt and user prompt template from AGENTS_SPEC.md.
Do not modify the prompts."
```

---

## CREDIT MANAGEMENT

| Phase | Platform | Investment |
|-------|----------|-----------|
| GCP credits | Google Cloud | $150 free |
| Lovable | 300 credits | Foundation (30) + Dashboard (70) + Inventory (50) + Outbreaks (40) + Orders (30) + Pipeline+Settings (40) + Fixes (40) = 300 |
| Claude Code | — | Unlimited (subscription) |
| Antigravity | Vertex AI | Within GCP $150 |
