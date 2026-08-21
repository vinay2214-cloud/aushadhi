"""AUSHADHI — agent base class.

Every agent in the pipeline is a BaseAgent subclass. The base class owns the
parts that must behave identically everywhere:

    run(center_id, payload)
        ├── _log_start()      -> writes a STARTED agent_logs document
        ├── process()         -> the subclass's work, retried on transient errors
        ├── _log_complete()   -> flips the document to COMPLETED with output
        └── _log_failure()    -> flips it to FAILED with the error, then re-raises

Subclasses implement process() only. Pub/Sub-driven agents also get
handle_message(), which is what PubSubService.subscribe() calls back into.

Agent logs are audit records, not control flow: if Firestore logging itself
fails, the agent's real work still counts, so logging errors are swallowed
with a warning rather than raised.
"""

import time
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from models.agent_log import AgentName
from services.firestore_service import FirestoreService, get_firestore_service
from services.pubsub_service import PubSubService, get_pubsub_service
from utils.logger import get_logger
from utils.retry import retry

log = get_logger(__name__)

# Agent-level retry sits on top of the per-service retries in
# FirestoreService/GeminiService/PubSubService, so it stays shallow: it only
# catches a whole-step failure that the service layer already gave up on.
agent_retry = retry(max_attempts=2, initial_delay=2.0, backoff_factor=2.0, max_delay=10.0)


class BaseAgent(ABC):
    """Shared lifecycle, logging, and Pub/Sub plumbing for all five agents."""

    #: Value written to agent_logs.agent_name — set by each subclass.
    name: AgentName
    #: Human-readable action label written to agent_logs.action.
    action: str = "run"
    #: Topic this agent publishes to (short name, no "aushadhi-" prefix).
    publishes_to: Optional[str] = None
    #: Subscription this agent consumes (short name), None for Sentinel.
    subscribes_to: Optional[str] = None

    def __init__(
        self,
        firestore: Optional[FirestoreService] = None,
        pubsub: Optional[PubSubService] = None,
    ) -> None:
        self.firestore = firestore or get_firestore_service()
        self.pubsub = pubsub or get_pubsub_service()
        self.log = get_logger(f"agents.{self.name.lower()}")

    # ───────────────────────────── LIFECYCLE ───────────────────────────

    async def run(self, center_id: Optional[str], payload: Dict[str, Any]) -> Dict[str, Any]:
        """Run this agent once: log start, process with retry, log the outcome."""
        log_id = await self._log_start(center_id, payload)
        started = time.perf_counter()

        self.log.info(
            "agent_started",
            agent=self.name,
            action=self.action,
            center_id=center_id,
            log_id=log_id,
        )

        try:
            result = await agent_retry(self.process)(center_id, payload)
        except Exception as exc:
            duration_ms = int((time.perf_counter() - started) * 1000)
            await self._log_failure(log_id, exc)
            self.log.error(
                "agent_failed",
                agent=self.name,
                action=self.action,
                center_id=center_id,
                log_id=log_id,
                duration_ms=duration_ms,
                error_type=type(exc).__name__,
                error=str(exc),
            )
            raise

        duration_ms = int((time.perf_counter() - started) * 1000)
        await self._log_complete(log_id, result, duration_ms)
        self.log.info(
            "agent_completed",
            agent=self.name,
            action=self.action,
            center_id=center_id,
            log_id=log_id,
            duration_ms=duration_ms,
        )
        return result

    @abstractmethod
    async def process(
        self, center_id: Optional[str], payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Do the agent's actual work and return a JSON-serializable result."""

    # ───────────────────────────── PUB/SUB ─────────────────────────────

    async def handle_message(self, message: Dict[str, Any]) -> None:
        """PubSubService.subscribe() callback: one message -> one run().

        Raising here makes PubSubService nack the message for redelivery.
        """
        center_id = message.get("center_id")
        await self.run(center_id, message)

    async def publish(self, message: Dict[str, Any], topic: Optional[str] = None) -> str:
        """Publish to this agent's downstream topic."""
        destination = topic or self.publishes_to
        if not destination:
            raise ValueError(f"{self.name} has no publishes_to topic configured")
        return await self.pubsub.publish(destination, message)

    # ─────────────────────────── AUDIT LOGGING ─────────────────────────

    async def _log_start(
        self, center_id: Optional[str], payload: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        try:
            return await self.firestore.log_agent_start(
                agent_name=self.name,
                center_id=center_id,
                action=self.action,
                input_data=_summarize(payload or {}),
            )
        except Exception as exc:
            self.log.warning(
                "agent_log_start_failed",
                agent=self.name,
                center_id=center_id,
                error_type=type(exc).__name__,
                error=str(exc),
            )
            return None

    async def _log_complete(
        self, log_id: Optional[str], result: Dict[str, Any], duration_ms: int = 0
    ) -> None:
        if not log_id:
            return
        try:
            await self.firestore.log_agent_complete(
                log_id=log_id,
                output_data=_summarize(result),
                duration_ms=duration_ms,
            )
        except Exception as exc:
            self.log.warning(
                "agent_log_complete_failed",
                agent=self.name,
                log_id=log_id,
                error_type=type(exc).__name__,
                error=str(exc),
            )

    async def _log_failure(
        self, log_id: Optional[str], error: BaseException, retry_count: int = 0
    ) -> None:
        if not log_id:
            return
        try:
            await self.firestore.log_agent_failure(
                log_id=log_id,
                error_message=f"{type(error).__name__}: {error}",
                retry_count=retry_count,
            )
        except Exception as exc:
            self.log.warning(
                "agent_log_failure_failed",
                agent=self.name,
                log_id=log_id,
                error_type=type(exc).__name__,
                error=str(exc),
            )


_MAX_LOGGED_LIST = 25
_MAX_LOGGED_STRING = 2000


def _summarize(data: Any) -> Any:
    """Trim payloads before they go into agent_logs.

    Firestore caps a document at 1 MiB and these payloads carry whole
    inventories and Gemini responses, so long lists and strings are truncated
    with a marker rather than risking a rejected write.
    """
    if isinstance(data, dict):
        return {key: _summarize(value) for key, value in data.items()}
    if isinstance(data, list):
        trimmed = [_summarize(item) for item in data[:_MAX_LOGGED_LIST]]
        if len(data) > _MAX_LOGGED_LIST:
            trimmed.append(f"... {len(data) - _MAX_LOGGED_LIST} more items truncated")
        return trimmed
    if isinstance(data, str) and len(data) > _MAX_LOGGED_STRING:
        return data[:_MAX_LOGGED_STRING] + f"... [{len(data)} chars truncated]"
    return data
