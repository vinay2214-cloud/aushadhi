# 🌿 AUSHADHI
### Autonomous Medicine Supply Intelligence System

> **All Things Agentic Hackathon** — Google | Track: The Taskmaster  
> Built by someone from Mandapeta, East Godavari, Andhra Pradesh — this problem is personal.

---

## The Problem

In rural India, an estimated 40% of health centers run out of essential medicines every month. Not because medicine doesn't exist — but because nobody is watching. A health worker fills paper registers. A clerk types them. A district officer reads a PDF three weeks later. By then, the child with dehydration was already turned away.

## The Solution

AUSHADHI is five AI agents that run continuously on Google Cloud, watching every health center, every medicine, every day:

```
[SENTINEL] detects stockout risk
    → [DQMS] validates data quality        ← Your DQMS project lives here
        → [FORECAST+OUTBREAK] Gemini predicts demand AND detects disease clusters ← The Twist
            → [PROCUREMENT] auto-generates purchase order  ← CrisisRoute logic
                → [ALERT] notifies district officer + generates report
```

**The Twist:** AUSHADHI detects disease outbreaks from medicine consumption patterns — before any patient is officially reported, before any manual surveillance system flags it. When ORS + Zinc + IV Saline consumption spikes 3.8x simultaneously across three health centers near a river delta, that is a cholera cluster forming. AUSHADHI flags it in 47 seconds.

---

## Live Demo

**Dashboard:** `https://aushadhi-frontend-[hash]-uc.a.run.app`  
**Demo Video:** `[YouTube URL]`

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| AI Model | Gemini 1.5 Flash (Gemini API / Vertex AI) |
| Agent Framework | Google ADK + Antigravity SDK |
| Offline Fallback | Gemma 2 9B (Vertex AI) |
| API | Python FastAPI |
| Primary Database | Google Cloud Firestore |
| Event Bus | Google Cloud Pub/Sub |
| Deployment | Google Cloud Run (3 services) |
| Scheduling | Google Cloud Scheduler (every 30 min) |
| Frontend | React 18 + TypeScript + Tailwind + shadcn/ui |
| Real-time | Server-Sent Events (SSE) |

---

## Quick Start (Local)

### Prerequisites
- Python 3.11+, Node.js 20+
- GCP project with Firestore + Pub/Sub enabled
- Gemini API key from [Google AI Studio](https://aistudio.google.com/app/apikey)

### Backend
```bash
cd backend
pip install -r requirements.txt
cp ../.env.example .env
# Edit .env: add GOOGLE_API_KEY and AUSHADHI_API_KEY

# Seed health center + inventory data (East Godavari district)
python3 ../scripts/seed_firestore.py

# Start API server
uvicorn main:app --reload --port 8000

# In a separate terminal: start agent workers
python3 -m agents.orchestrator
```

### Frontend
```bash
cd frontend
npm install
cp .env.example .env.local
# Set VITE_API_BASE_URL=http://localhost:8000

npm run dev
# Open http://localhost:5173
```

### Trigger the Pipeline
```bash
# This fires all 5 agents — watch the dashboard update live
curl -X POST http://localhost:8000/api/v1/internal/run-sentinel \
  -H "X-API-Key: your-api-key"

# Or trigger the cholera outbreak demo scenario
curl -X POST http://localhost:8000/api/v1/internal/simulate-outbreak \
  -H "X-API-Key: your-api-key"
```

---

## Architecture

![AUSHADHI Architecture](architecture/aushadhi-architecture.png)

Five decoupled agents communicate via Google Pub/Sub. All state persists to Firestore. The frontend receives real-time updates via SSE. Cloud Scheduler triggers the Sentinel every 30 minutes.

---

## Documentation

| Doc | Purpose |
|-----|---------|
| [PRD.md](docs/PRD.md) | What we built and why |
| [AGENTS_SPEC.md](docs/AGENTS_SPEC.md) | Agent definitions + exact Gemini prompts |
| [DATABASE_SCHEMA.md](docs/DATABASE_SCHEMA.md) | All Firestore collections |
| [API_CONTRACTS.md](docs/API_CONTRACTS.md) | All API endpoints |
| [FRONTEND_SPEC.md](docs/FRONTEND_SPEC.md) | Frontend screens + Lovable guide |
| [DEPLOYMENT.md](docs/DEPLOYMENT.md) | GCP deployment steps |
| [DEMO_SCRIPT.md](DEMO_SCRIPT.md) | Word-for-word 4-minute demo |
| [PLAN_OF_APPROACH.md](PLAN_OF_APPROACH.md) | Day-by-day build schedule |

---

## Impact

India has 160,000 rural health facilities. Most run blind. AUSHADHI is the system that watches them — and the system that could detect the next cholera outbreak 3–5 days before any surveillance system does.

This is not just a hackathon project. This is a real system for a real problem.

---

*Built with Google Gemini, Google ADK, Google Cloud — #AllThingsAgenticHackathon*  
*From Mandapeta, East Godavari — the district where this problem is personal.*
