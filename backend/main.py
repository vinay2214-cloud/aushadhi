"""AUSHADHI — FastAPI application entrypoint.

Run locally — one command starts the whole system:
    cd backend && uvicorn main:app --reload --port 8000

The four Pub/Sub subscriber loops (DQMS, FORECAST, PROCUREMENT, ALERT) run as a
background task inside this process, so there is no second worker process to
start. Set AGENTS_IN_PROCESS=false to serve HTTP only — needed when running
more than one API replica, since every replica would otherwise consume the same
subscriptions and duplicate the Gemini calls.
"""

import asyncio
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.middleware.auth import APIKeyMiddleware
from api.router import api_router
from config import settings
from utils.logger import configure_logging, get_logger

configure_logging()
log = get_logger(__name__)

API_V1_PREFIX = "/api/v1"

#: Per-probe ceiling for /health. A gRPC call with no deadline can hang
#: indefinitely, which would wedge Cloud Run's health check; a slow
#: dependency should report "timeout", not stall the probe.
HEALTH_PROBE_TIMEOUT_SECONDS = 5.0

@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info(
        "aushadhi_api_starting",
        version=settings.app_version,
        environment=settings.environment,
        run_mode=settings.run_mode,
        project=settings.google_cloud_project,
        region=settings.google_cloud_region,
        gemini_model=settings.gemini_model,
        vertex_location=settings.vertex_location,
        api_key_configured=bool(settings.aushadhi_api_key),
        agents_in_process=settings.agents_in_process,
    )

    orchestrator = None
    if settings.agents_in_process:
        # Imported lazily so the module's Firestore/Pub/Sub clients are only
        # built when the agents actually run.
        from agents.orchestrator import get_orchestrator

        orchestrator = get_orchestrator()
        orchestrator.start_background()
    else:
        log.warning("agent_orchestrator_disabled", reason="AGENTS_IN_PROCESS=false")

    yield

    if orchestrator is not None:
        await orchestrator.stop_background()

    log.info("aushadhi_api_stopped")


app = FastAPI(
    title=f"{settings.app_name} API",
    description="Autonomous medicine supply intelligence for rural healthcare in Andhra Pradesh",
    version=settings.app_version,
    lifespan=lifespan,
)

# Middleware runs in reverse registration order, so CORS is added last and
# therefore wraps the auth check — a rejected key still comes back with CORS
# headers instead of surfacing in the browser as an opaque network error.
app.add_middleware(APIKeyMiddleware)
# allow_credentials=True makes the wildcard forms of allow_methods/allow_headers
# reflect rather than emit "*", so the effective set is spelled out here: the
# dashboard only ever issues these verbs, and X-API-Key is the header the auth
# middleware reads (a preflight that omits it from allow_headers fails before
# the real request is ever sent).
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["X-API-Key", "Content-Type", "Authorization"],
)

app.include_router(api_router, prefix=API_V1_PREFIX)


async def _probe_firestore() -> str:
    """Read system_config/main_config — proves credentials and connectivity."""
    try:
        from services.firestore_service import get_firestore_service

        snap = await get_firestore_service().db.collection("system_config").document(
            "main_config"
        ).get()
        return "connected" if snap.exists else "connected_no_config"
    except Exception as exc:
        log.error("health_firestore_probe_failed", error_type=type(exc).__name__, error=str(exc))
        return "error"


async def _probe_pubsub() -> str:
    try:
        from services.pubsub_service import get_pubsub_service

        topics = await get_pubsub_service().list_topics(
            timeout=HEALTH_PROBE_TIMEOUT_SECONDS
        )
        return "connected" if topics else "connected_no_topics"
    except Exception as exc:
        log.error("health_pubsub_probe_failed", error_type=type(exc).__name__, error=str(exc))
        return "error"


def _probe_gemini() -> str:
    """Client construction only — no live call, so /health costs nothing."""
    try:
        from services.gemini_service import get_gemini_service

        get_gemini_service()
        return "configured"
    except Exception as exc:
        log.error("health_gemini_probe_failed", error_type=type(exc).__name__, error=str(exc))
        return "error"


async def _with_timeout(coro, name: str) -> str:
    """Bound a probe so one unresponsive dependency cannot stall /health."""
    try:
        return await asyncio.wait_for(coro, timeout=HEALTH_PROBE_TIMEOUT_SECONDS)
    except asyncio.TimeoutError:
        log.error("health_probe_timeout", probe=name, timeout=HEALTH_PROBE_TIMEOUT_SECONDS)
        return "timeout"


@app.get("/health", tags=["system"])
async def health() -> dict:
    """Liveness probe with real service checks. No auth required."""
    firestore_status, pubsub_status = await asyncio.gather(
        _with_timeout(_probe_firestore(), "firestore"),
        _with_timeout(_probe_pubsub(), "pubsub"),
    )
    gemini_status = await _with_timeout(asyncio.to_thread(_probe_gemini), "gemini")

    services = {
        "firestore": firestore_status,
        "pubsub": pubsub_status,
        "gemini": gemini_status,
    }
    healthy = not any(status in ("error", "timeout") for status in services.values())

    return {
        "status": "healthy" if healthy else "degraded",
        "version": settings.app_version,
        "environment": settings.environment,
        "run_mode": settings.run_mode,
        "services": services,
        "gemini_auth": "vertex_ai",
        "gemini_model": settings.gemini_model,
        "vertex_location": settings.vertex_location,
    }
