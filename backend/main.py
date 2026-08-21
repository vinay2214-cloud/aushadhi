"""AUSHADHI — FastAPI application entrypoint.

Run locally:
    cd backend && uvicorn main:app --reload

Two run modes, selected by RUN_MODE:
    api    (default) — serve HTTP only; a separate process runs the agents
    agents           — also start the four Pub/Sub subscriber loops in-process,
                       so one container runs the whole pipeline (handy for the
                       demo, and for Cloud Run with a single service)
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

_subscriber_task: Optional[asyncio.Task] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _subscriber_task

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
    )

    if settings.run_mode == "agents":
        from agents.orchestrator import get_orchestrator

        orchestrator = get_orchestrator()
        _subscriber_task = asyncio.create_task(
            orchestrator.start_subscribers(), name="pubsub-subscribers"
        )
        log.info("aushadhi_subscribers_started_in_process")

    yield

    if _subscriber_task is not None:
        from agents.orchestrator import get_orchestrator

        await get_orchestrator().stop()
        _subscriber_task.cancel()
        try:
            await _subscriber_task
        except (asyncio.CancelledError, Exception):  # noqa: B014 - shutdown is best effort
            pass

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
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
