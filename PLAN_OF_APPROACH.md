# AUSHADHI — 11-Day Build Plan
> Start: August 20 | Deadline: August 31, 5PM PT | Today is Day 1.

---

## DAY 1 (Aug 20) — GCP + Foundation
- [ ] Claim $150 Google Cloud credits (hackathon form — deadline Aug 28)
- [ ] Create GCP project: `aushadhi-hackathon`
- [ ] Enable APIs: Cloud Run, Firestore, Pub/Sub, Scheduler, Secret Manager, Gemini
- [ ] Get Gemini API key from Google AI Studio
- [ ] Create backend scaffold with Claude Code (give: FILE_STRUCTURE.md)
- [ ] Create Firestore database (native mode, us-central1)
- [ ] Run seed script: `python3 scripts/seed_firestore.py` → 8 health centers, 10 medicines
- [ ] Verify: Firestore has health_centers + inventory collections populated
- [ ] Commit to GitHub

## DAY 2 (Aug 21) — Core Services + Sentinel Agent
- [ ] Give Claude Code: DATABASE_SCHEMA.md + AGENTS_SPEC.md (Sentinel section)
- [ ] Build: `services/firestore_service.py` (CRUD for all collections)
- [ ] Build: `services/pubsub_service.py` (publish + subscribe)
- [ ] Build: `agents/sentinel_agent.py` (scan_all_centers logic)
- [ ] Build: `api/routes/inventory.py` + `api/routes/health_centers.py`
- [ ] Test: `GET /api/v1/inventory?urgency=CRITICAL` returns Razole items
- [ ] Commit

## DAY 3 (Aug 22) — DQMS + Forecast Agents (The Heart)
- [ ] Give Claude Code: AGENTS_SPEC.md DQMS section
- [ ] Build: `agents/dqms_agent.py` (port your DQMS validation rules)
- [ ] Give Claude Code: AGENTS_SPEC.md Forecast+Outbreak section + EXACT PROMPTS
- [ ] Build: `services/gemini_service.py` wrapper
- [ ] Build: `agents/forecast_agent.py` with both prompts (copy from AGENTS_SPEC.md)
- [ ] Test: Trigger pipeline → Gemini classifies Razole as CHOLERA HIGH
- [ ] Print Gemini's JSON response to verify outbreak detection works
- [ ] **THIS IS THE MOST IMPORTANT TEST OF THE BUILD**
- [ ] Commit

## DAY 4 (Aug 23) — Procurement + Alert + Orchestrator
- [ ] Build: `agents/procurement_agent.py` (haversine routing from CrisisRoute)
- [ ] Build: `agents/alert_agent.py` (notification templates from AGENTS_SPEC.md)
- [ ] Build: `agents/orchestrator.py` (all 4 Pub/Sub subscriptions)
- [ ] Run full pipeline end-to-end: POST /internal/run-sentinel → watch all 5 agents fire
- [ ] Verify: purchase_order created in Firestore, outbreak_alert created
- [ ] Commit

## DAY 5 (Aug 24) — SSE + Remaining APIs
- [ ] Build: `api/routes/stream.py` (SSE with Firestore listener)
- [ ] Build: `api/routes/outbreaks.py`, `api/routes/purchase_orders.py`
- [ ] Build: `api/routes/agents.py`, `api/routes/metrics.py`
- [ ] Test SSE: `curl -N $API_URL/api/v1/stream?api_key=xxx`
- [ ] Build: `api/routes/internal.py` (run-sentinel, simulate-outbreak endpoints)
- [ ] Run 3 complete pipeline simulations, verify all data flows
- [ ] Commit

## DAY 6 (Aug 25) — Lovable Frontend (Days 6–8)
Lovable budget: 300 credits

- [ ] Open Lovable → new project "AUSHADHI"
- [ ] Send Master Prompt from FRONTEND_SPEC.md
- [ ] Send TypeScript types
- [ ] Send Dashboard page prompt (70 credits)
- [ ] Export and verify: dark theme, metrics row, health center cards
- [ ] Set VITE_API_BASE_URL=http://localhost:8000, test against running backend
- [ ] Commit frontend code to GitHub

## DAY 7 (Aug 26) — Frontend Pages 2–3
- [ ] Send Inventory heatmap prompt to Lovable (50 credits)
- [ ] Send Outbreaks intelligence prompt (40 credits)
- [ ] Test: connect to backend, verify outbreak alert banner shows for Razole
- [ ] Fix SSE connection (ensure api_key in URL param works)
- [ ] Commit

## DAY 8 (Aug 27) — Frontend Pages 4–6 + Polish
- [ ] Send Purchase Orders prompt (30 credits)
- [ ] Send Pipeline + Settings prompts (40 credits)
- [ ] Remaining 40 credits: fix any bugs, polish UI
- [ ] Full end-to-end test: trigger pipeline from frontend → watch all pages update
- [ ] Commit

## DAY 9 (Aug 28) — GCP Deployment
- [ ] Build Docker images + push to Artifact Registry
- [ ] Deploy aushadhi-api to Cloud Run
- [ ] Deploy aushadhi-agents to Cloud Run
- [ ] Set up Cloud Scheduler (sentinel every 30 min)
- [ ] Deploy frontend to Cloud Run
- [ ] Test complete production URL
- [ ] Screenshot Cloud Run dashboard (for demo video)
- [ ] Claim Google Cloud credits (DEADLINE TODAY Aug 28, 12PM PT)

## DAY 10 (Aug 29) — Architecture Diagram + Demo Prep
- [ ] Draw architecture diagram in draw.io (see ARCHITECTURE.md for component list)
- [ ] Export as PNG → commit to architecture/ folder
- [ ] Finalize README.md with complete spin-up instructions
- [ ] Practice demo script 5 times (DEMO_SCRIPT.md)
- [ ] Record test run, time each section

## DAY 11 (Aug 30) — Record Demo + Bonus Points
Morning:
- [ ] Record final 4-minute demo video (follow DEMO_SCRIPT.md word for word)
- [ ] Upload to YouTube (Public) — copy URL

Afternoon:
- [ ] Write Dev.to article: "How I built AUSHADHI: AI agents that detect disease outbreaks"
  - Include architecture diagram, code snippets from Forecast Agent, Gemini prompts
  - Add: "Created for #AllThingsAgenticHackathon"
  - Publish publicly
- [ ] Post on LinkedIn with #AllThingsAgenticHackathon

## DAY 12 (Aug 31) — Final Submission (by 5PM PT)
Morning:
- [ ] Final smoke test on production URL
- [ ] Verify GitHub repo is clean (README, architecture diagram, spin-up instructions)

Afternoon:
- [ ] Go to allthingsagentichackathon.devpost.com → "Enter a Submission"
- [ ] Fill ALL fields:
  - Project: AUSHADHI — Autonomous Medicine Supply Intelligence
  - Hosted URL: [frontend Cloud Run URL]
  - Category: The Taskmaster
  - GitHub: [your public repo]
  - Video: [YouTube URL]
  - Tech stack: Gemini 1.5 Flash, Google ADK, Cloud Run, Firestore, Pub/Sub, Cloud Scheduler, React, Python FastAPI
  - Content link: [Dev.to article]
  - Social post link: [LinkedIn URL]
- [ ] SUBMIT ✅

## DAILY COST CONTROL
Every evening run:
```bash
gcloud run services update aushadhi-api --min-instances=0 --region=us-central1
gcloud run services update aushadhi-agents --min-instances=0 --region=us-central1
gcloud scheduler jobs pause sentinel-poll --location=us-central1
echo "✅ Costs stopped for tonight"
```
