"""AUSHADHI — agent status + agent log endpoints.

Everything here is derived from the `agent_logs` collection each agent writes
through BaseAgent (STARTED -> COMPLETED/FAILED), so the dashboard reflects what
the pipeline actually did rather than a separately maintained status table.
"""

from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, Depends, Query
from google.cloud.firestore_v1.base_query import FieldFilter

from api.deps import (
    firestore,
    paginate,
    pagination,
    parse_period,
    utc_now_iso,
    window_start_iso,
)
from api.schemas import AgentStatus, AgentStatusResponse, PaginatedResponse
from models.agent_log import AgentLog
from services.firestore_service import FirestoreService
from utils.logger import get_logger

log = get_logger(__name__)

router = APIRouter(tags=["agents"])

COLL = "agent_logs"
AGENT_NAMES = ("SENTINEL", "DQMS", "FORECAST", "PROCUREMENT", "ALERT")


async def _logs_since(svc: FirestoreService, since_iso: str) -> List[Dict[str, Any]]:
    query = svc.db.collection(COLL).where(
        filter=FieldFilter("created_at", ">=", since_iso)
    )
    return [snap.to_dict() async for snap in query.stream()]


def _health(runs: int, failures: int, in_flight: int) -> str:
    if runs == 0:
        return "IDLE"
    if failures == 0:
        return "HEALTHY"
    if failures >= runs:
        return "FAILING"
    return "DEGRADED"


@router.get("/agents/status", response_model=AgentStatusResponse)
async def agents_status(
    period: str = Query("24h", description="Rolling window, e.g. 60m, 24h, 7d"),
    svc: FirestoreService = Depends(firestore),
) -> AgentStatusResponse:
    window = parse_period(period)
    entries = await _logs_since(svc, window_start_iso(window))

    by_agent: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for entry in entries:
        by_agent[entry.get("agent_name", "UNKNOWN")].append(entry)

    rows: List[AgentStatus] = []
    for name in AGENT_NAMES:
        agent_entries = by_agent.get(name, [])
        completed = [e for e in agent_entries if e.get("status") == "COMPLETED"]
        failed = [e for e in agent_entries if e.get("status") == "FAILED"]
        started = [e for e in agent_entries if e.get("status") == "STARTED"]
        durations = [e.get("duration_ms", 0) for e in completed if e.get("duration_ms")]

        row: Dict[str, Any] = {
            "name": name,
            "status": _health(len(completed) + len(failed), len(failed), len(started)),
            "last_run": max((e.get("created_at", "") for e in agent_entries), default=None) or None,
            "runs_today": len(completed) + len(failed),
            "failures_today": len(failed),
            "avg_duration_ms": int(sum(durations) / len(durations)) if durations else 0,
        }

        outputs = [e.get("output") or {} for e in completed]

        # Per-agent extras, matching docs/API_CONTRACTS.md.
        if name == "DQMS":
            validated = sum(int(o.get("total_records") or 0) for o in outputs)
            rejected = sum(int(o.get("rejected_records") or 0) for o in outputs)
            row["records_validated_today"] = validated
            row["rejection_rate"] = round(rejected / validated, 3) if validated else 0.0
        elif name == "FORECAST":
            forecasts = sum(int(o.get("forecasts_generated") or 0) for o in outputs)
            analyses = [o.get("outbreak") or {} for o in outputs]
            analysed = [a for a in analyses if a.get("analyzed")]
            confidences = [
                float(a["confidence"]) for a in analysed if a.get("confidence") is not None
            ]
            # One Gemini call per forecast, plus one per district outbreak analysis.
            row["gemini_calls_today"] = forecasts + len(analysed)
            row["forecasts_generated_today"] = forecasts
            row["outbreaks_detected_today"] = sum(
                1 for a in analysed if a.get("outbreak_detected")
            )
            row["avg_confidence"] = (
                round(sum(confidences) / len(confidences), 3) if confidences else 0.0
            )
        elif name == "PROCUREMENT":
            row["pos_generated_today"] = sum(
                len(o.get("purchase_orders") or []) for o in outputs
            )
        elif name == "ALERT":
            row["alerts_sent_today"] = sum(
                int(o.get("notifications_sent") or 0) for o in outputs
            )
        elif name == "SENTINEL":
            row["centers_scanned_last_run"] = next(
                (int(o.get("centers_scanned") or 0) for o in reversed(outputs)), 0
            )
            row["alerts_published_today"] = sum(
                len(o.get("published") or []) for o in outputs
            )

        rows.append(AgentStatus(**row))

    return AgentStatusResponse(
        agents=rows,
        window_hours=round(window.total_seconds() / 3600, 2),
        generated_at=utc_now_iso(),
    )


@router.get("/agent-logs", response_model=PaginatedResponse[AgentLog])
async def list_agent_logs(
    agent_name: Optional[str] = Query(None, description="SENTINEL | DQMS | FORECAST | PROCUREMENT | ALERT"),
    center_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None, description="STARTED | COMPLETED | FAILED | RETRYING"),
    period: str = Query("24h"),
    page: Tuple[int, int] = Depends(pagination),
    svc: FirestoreService = Depends(firestore),
) -> PaginatedResponse[AgentLog]:
    limit, offset = page
    entries = await _logs_since(svc, window_start_iso(parse_period(period)))

    logs: List[AgentLog] = []
    for entry in entries:
        try:
            logs.append(AgentLog(**entry))
        except Exception as exc:
            log.error("agent_log_validation_failed", doc_id=entry.get("id"), error=str(exc))

    if agent_name:
        logs = [entry for entry in logs if entry.agent_name == agent_name.upper()]
    if center_id:
        logs = [entry for entry in logs if entry.center_id == center_id]
    if status:
        logs = [entry for entry in logs if entry.status == status.upper()]

    logs.sort(key=lambda entry: entry.created_at, reverse=True)
    items, total = paginate(logs, limit, offset)
    return PaginatedResponse.build(items, total, limit, offset)
