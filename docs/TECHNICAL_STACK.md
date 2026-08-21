# AUSHADHI — Technical Stack (All Versions Pinned)

---

## FRONTEND

| Package | Version | Purpose |
|---------|---------|---------|
| react | 18.3.1 | UI framework |
| typescript | 5.4.5 | Type safety |
| vite | 5.2.11 | Build tool |
| react-router-dom | 6.24.0 | Client routing |
| @tanstack/react-query | 5.45.0 | Server state |
| zustand | 4.5.2 | Client state |
| axios | 1.7.2 | HTTP client |
| tailwindcss | 3.4.4 | CSS |
| shadcn/ui | latest | Components |
| lucide-react | 0.383.0 | Icons |
| recharts | 2.12.7 | Charts |
| leaflet | 1.9.4 | Maps |
| react-leaflet | 4.2.1 | React maps |
| @types/leaflet | 1.9.12 | Map types |
| date-fns | 3.6.0 | Date utils |
| react-hot-toast | 2.4.1 | Notifications |
| clsx | 2.1.1 | Class utils |
| tailwind-merge | 2.3.0 | Class merging |

---

## BACKEND (Python)

Save as `backend/requirements.txt`:
```
fastapi==0.111.1
uvicorn[standard]==0.30.1
pydantic==2.7.4
pydantic-settings==2.3.4
google-genai>=1.0.0
google-cloud-aiplatform==1.57.0
google-cloud-firestore==2.16.0
google-cloud-pubsub==2.21.4
google-cloud-logging==3.10.0
google-cloud-secret-manager==2.20.0
google-auth==2.30.0
sse-starlette==2.1.0
httpx==0.27.0
tenacity==8.4.1
haversine==2.8.1
structlog==24.2.0
python-dotenv==1.0.1
pytz==2024.1
```

Save as `backend/requirements-dev.txt`:
```
-r requirements.txt
pytest==8.2.2
pytest-asyncio==0.23.7
black==24.4.2
ruff==0.5.0
```

Save as `scripts/requirements.txt` (for test + seed scripts):
```
google-genai>=1.0.0
google-cloud-firestore==2.16.0
python-dotenv==1.0.1
haversine==2.8.1
```

---

## GCP SERVICES

| Service | Config | Purpose |
|---------|--------|---------|
| Cloud Run | us-central1, min=0, max=5 | API + Agent workers |
| Firestore | Native mode, us-central1 | All data storage |
| Pub/Sub | us-central1 | Agent event bus |
| Cloud Scheduler | us-central1, every 30 min | Trigger Sentinel |
| Secret Manager | Global | Store API keys |
| Artifact Registry | us-central1 | Docker images |
| Cloud Logging | Default | Audit trail |

## PUB/SUB TOPICS

| Topic | Producer | Consumer |
|-------|---------|---------|
| aushadhi-sentinel-alerts | Sentinel | DQMS Agent |
| aushadhi-validated-data | DQMS | Forecast Agent |
| aushadhi-forecast-complete | Forecast | Procurement Agent |
| aushadhi-procured | Procurement | Alert Agent |
| aushadhi-dead-letter | All (on failure) | Admin |

## CLOUD RUN SERVICES

| Service | Memory | CPU | Min | Purpose |
|---------|--------|-----|-----|---------|
| aushadhi-api | 1Gi | 1 | 0 | FastAPI + SSE |
| aushadhi-agents | 2Gi | 2 | 1 | Agent workers |
| aushadhi-frontend | 256Mi | 0.5 | 0 | React app |
