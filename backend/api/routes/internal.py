"""AUSHADHI — internal trigger endpoints (Cloud Scheduler + demo controls).

Both endpoints return 202 immediately and do the work in the background: a
sentinel cycle takes tens of seconds and a reseed writes several hundred
documents, neither of which should hold an HTTP connection open.
"""

import asyncio
import importlib.util
import sys
import uuid
from pathlib import Path
from typing import Any, Dict, Optional, Set

from fastapi import APIRouter, Query, status

from api.deps import utc_now_iso
from api.schemas import TriggerResponse
from agents.orchestrator import get_orchestrator
from config import PROJECT_ROOT
from utils.logger import get_logger

log = get_logger(__name__)

router = APIRouter(tags=["internal"])

SEED_SCRIPT = PROJECT_ROOT / "scripts" / "seed_firestore.py"

#: asyncio only holds a weak reference to a bare task, so keep them here until
#: they finish or a mid-flight cycle could be garbage collected.
_background_tasks: Set[asyncio.Task] = set()


def _spawn(coro, name: str) -> asyncio.Task:
    task = asyncio.create_task(coro, name=name)
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
    return task


async def _run_sentinel(district: Optional[str], cycle_id: str) -> None:
    try:
        result = await get_orchestrator().run_sentinel_cycle(
            district=district, cycle_id=cycle_id
        )
        log.info(
            "internal_sentinel_cycle_finished",
            cycle_id=cycle_id,
            centers_alerting=result.get("centers_alerting"),
            centers_scanned=result.get("centers_scanned"),
        )
    except Exception as exc:
        log.error(
            "internal_sentinel_cycle_failed",
            cycle_id=cycle_id,
            error_type=type(exc).__name__,
            error=str(exc),
        )


@router.post(
    "/internal/run-sentinel",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=TriggerResponse,
)
async def run_sentinel(
    district: Optional[str] = Query(None, description="Limit the cycle to one district"),
) -> TriggerResponse:
    """Trigger a sentinel cycle. Cloud Scheduler calls this every 30 minutes."""
    cycle_id = f"cycle_{uuid.uuid4().hex[:12]}"
    _spawn(_run_sentinel(district, cycle_id), name=f"sentinel:{cycle_id}")
    log.info("internal_sentinel_cycle_started", cycle_id=cycle_id, district=district or "ALL")
    return TriggerResponse(
        message="Sentinel cycle started",
        cycle_id=cycle_id,
        district=district or "ALL",
        started_at=utc_now_iso(),
    )


def _load_seed_module():
    """Import scripts/seed_firestore.py by path.

    It lives outside the backend package and builds its own sync Firestore
    client at import time, so it is loaded on demand rather than at startup.
    """
    if not SEED_SCRIPT.exists():
        raise FileNotFoundError(f"seed script not found at {SEED_SCRIPT}")
    module_name = "aushadhi_seed_firestore"
    if module_name in sys.modules:
        return sys.modules[module_name]
    spec = importlib.util.spec_from_file_location(module_name, SEED_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _reseed_scenario() -> Dict[str, Any]:
    """Re-run the seed script's scenario functions in-process (no subprocess).

    Resets health center status, inventory levels, and the 7-day consumption
    history back to the Razole/Amalapuram cholera signature. Medicines and
    warehouses are reference data and are left alone.
    """
    seed = _load_seed_module()
    seed.seed_health_centers()
    seed.seed_inventory()
    seed.seed_consumption_history()
    return {
        "centers": len(seed.HEALTH_CENTERS),
        "medicines": len(seed.MEDICINES),
        "outbreak_centers": ["phc_razole_001", "phc_amalapuram_002"],
    }


async def _run_simulate() -> None:
    try:
        # The seed module is synchronous Firestore — keep it off the event loop.
        summary = await asyncio.to_thread(_reseed_scenario)
        log.info("internal_simulate_outbreak_finished", **summary)
    except Exception as exc:
        log.error(
            "internal_simulate_outbreak_failed",
            error_type=type(exc).__name__,
            error=str(exc),
        )


@router.post(
    "/internal/simulate-outbreak",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=TriggerResponse,
)
async def simulate_outbreak() -> TriggerResponse:
    """Demo trigger: reload the Razole mandal cholera scenario into Firestore."""
    _spawn(_run_simulate(), name="simulate-outbreak")
    log.info("internal_simulate_outbreak_started")
    return TriggerResponse(
        message="Outbreak scenario loaded for Razole mandal",
        scenario="CHOLERA_OUTBREAK",
        affected_centers=["phc_razole_001", "phc_amalapuram_002"],
        note="Run POST /api/v1/internal/run-sentinel to push it through the pipeline",
        started_at=utc_now_iso(),
    )
