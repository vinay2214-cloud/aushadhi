"""AUSHADHI — internal trigger endpoints (Cloud Scheduler + demo controls).

Every endpoint returns 202 immediately and does the work in the background: a
sentinel cycle takes tens of seconds, a full pipeline run takes minutes, and a
reseed writes several hundred documents — none of which should hold an HTTP
connection open.

    run-sentinel        starts the cycle and lets Pub/Sub carry it downstream
    run-full-pipeline   runs all five agents in this process, back to back
    simulate-outbreak   reloads the Razole cholera scenario into Firestore
"""

import asyncio
import importlib.util
import sys
import uuid
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from fastapi import APIRouter, Query, status

from api.deps import utc_now_iso
from api.schemas import TriggerResponse
from agents.orchestrator import get_orchestrator
from config import PROJECT_ROOT
from services.firestore_service import get_firestore_service
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


# ══════════════════════════════════════════════════════════════════════════
#  FULL PIPELINE — all five agents, sequentially, in this process
# ══════════════════════════════════════════════════════════════════════════
#
# run-sentinel publishes to Pub/Sub and the four subscriber loops carry the
# cycle downstream. That is the production path, but it makes the Pipeline
# page depend on subscriber delivery timing, and a cycle that loses one
# message leaves later agents with nothing to show.
#
# This endpoint runs the same five agents against the same Firestore data,
# handing each agent's outgoing message straight to the next one. Every agent
# still goes through BaseAgent.run(), so each writes its own STARTED ->
# COMPLETED agent_logs document exactly as it does under Pub/Sub — that is
# what the Pipeline page reads.


class _LocalBus:
    """Stands in for PubSubService: captures published messages, sends nothing.

    The agents are handed this instead of the real client so a full-pipeline
    run stays inside this process. Publishing for real would put the same
    messages in front of the orchestrator's subscriber loops, which would run
    the whole chain a second time and double every Gemini call.
    """

    def __init__(self) -> None:
        self.topics: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

    async def publish(
        self, topic_name: str, message_dict: Dict[str, Any], **attributes: str
    ) -> str:
        self.topics[topic_name].append(message_dict)
        return f"local-{uuid.uuid4().hex[:12]}"

    def drain(self, topic_name: str) -> List[Dict[str, Any]]:
        """Take everything queued on a topic, leaving it empty."""
        return self.topics.pop(topic_name, [])


async def _run_stage(agent, messages: List[Dict[str, Any]], cycle_id: str) -> int:
    """Run one agent once per inbound message. Returns the number of runs.

    A single center failing is not a reason to abandon the cycle — under
    Pub/Sub the message would simply be nacked and the other centers would
    carry on — so a raised agent is logged and the stage continues.
    """
    completed = 0
    for message in messages:
        try:
            await agent.run(message.get("center_id"), message)
            completed += 1
        except Exception as exc:
            log.error(
                "full_pipeline_agent_failed",
                cycle_id=cycle_id,
                agent=agent.name,
                center_id=message.get("center_id"),
                error_type=type(exc).__name__,
                error=str(exc),
            )
    return completed


async def _run_full_pipeline(cycle_id: str, district: Optional[str]) -> None:
    """SENTINEL -> DQMS -> FORECAST -> PROCUREMENT -> ALERT, back to back."""
    from agents.alert_agent import AlertReportAgent
    from agents.dqms_agent import DQMSValidationAgent
    from agents.forecast_agent import ForecastOutbreakAgent
    from agents.procurement_agent import ProcurementAgent
    from agents.sentinel_agent import InventorySentinelAgent

    bus = _LocalBus()
    firestore = get_firestore_service()
    stages: Dict[str, int] = {}

    log.info("full_pipeline_started", cycle_id=cycle_id, district=district or "ALL")

    try:
        # ── Agent 1: SENTINEL ── one run over every center in scope.
        log.info("full_pipeline_phase", cycle_id=cycle_id, agent="SENTINEL")
        sentinel = InventorySentinelAgent(firestore, bus)
        result = await sentinel.scan_all_centers(district=district, cycle_id=cycle_id)
        stages["sentinel"] = 1
        alerts = bus.drain("sentinel-alerts")
        log.info(
            "full_pipeline_phase_done",
            cycle_id=cycle_id,
            agent="SENTINEL",
            centers_scanned=result.get("centers_scanned"),
            centers_alerting=result.get("centers_alerting"),
            messages=len(alerts),
        )

        # ── Agent 2: DQMS ── one run per alerting center.
        log.info("full_pipeline_phase", cycle_id=cycle_id, agent="DQMS", inbound=len(alerts))
        dqms = DQMSValidationAgent(firestore, bus)
        stages["dqms"] = await _run_stage(dqms, alerts, cycle_id)
        validated = bus.drain("validated-data")

        # ── Agent 3: FORECAST + OUTBREAK ── the Gemini stage.
        # Under Pub/Sub this agent buffers a district until every center has
        # reported before it runs detect_outbreak. Here the whole cycle is
        # already in hand, so any buffer left over is flushed straight away
        # rather than waiting on the orchestrator's 20s sweep.
        log.info("full_pipeline_phase", cycle_id=cycle_id, agent="FORECAST", inbound=len(validated))
        forecast = ForecastOutbreakAgent(firestore, bus)
        stages["forecast"] = await _run_stage(forecast, validated, cycle_id)
        try:
            await forecast.flush_pending()
        except Exception as exc:
            log.error(
                "full_pipeline_flush_failed",
                cycle_id=cycle_id,
                error_type=type(exc).__name__,
                error=str(exc),
            )
        forecast_complete = bus.drain("forecast-complete")

        # ── Agent 4: PROCUREMENT ── one run per center that got a forecast.
        log.info(
            "full_pipeline_phase",
            cycle_id=cycle_id,
            agent="PROCUREMENT",
            inbound=len(forecast_complete),
        )
        procurement = ProcurementAgent(firestore, bus)
        stages["procurement"] = await _run_stage(procurement, forecast_complete, cycle_id)
        procured = bus.drain("procured")

        # ── Agent 5: ALERT ── one run per purchase order raised.
        log.info("full_pipeline_phase", cycle_id=cycle_id, agent="ALERT", inbound=len(procured))
        alert = AlertReportAgent(firestore, bus)
        stages["alert"] = await _run_stage(alert, procured, cycle_id)

        skipped = [name for name, runs in stages.items() if runs == 0]
        log.info(
            "full_pipeline_completed",
            cycle_id=cycle_id,
            district=district or "ALL",
            agents_run=sum(1 for runs in stages.values() if runs),
            # A stage with no inbound messages never ran, so it will not appear
            # on the Pipeline page. That means the stage above it produced
            # nothing to act on (no alerting centers, nothing urgent enough to
            # order), not that an agent is broken.
            stages_skipped=skipped or None,
            **{f"{name}_runs": runs for name, runs in stages.items()},
        )
    except Exception as exc:
        log.error(
            "full_pipeline_failed",
            cycle_id=cycle_id,
            stages_completed=stages,
            error_type=type(exc).__name__,
            error=str(exc),
        )


@router.post(
    "/internal/run-full-pipeline",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=TriggerResponse,
)
async def run_full_pipeline(
    district: Optional[str] = Query(None, description="Limit the run to one district"),
) -> TriggerResponse:
    """Run all five agents in sequence, without going through Pub/Sub."""
    cycle_id = f"full_{uuid.uuid4().hex[:8]}"
    _spawn(_run_full_pipeline(cycle_id, district), name=f"full-pipeline:{cycle_id}")
    log.info("internal_full_pipeline_started", cycle_id=cycle_id, district=district or "ALL")
    return TriggerResponse(
        message="Full pipeline started — all 5 agents will run sequentially",
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
