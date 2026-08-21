"""AUSHADHI — orchestrator.

Owns all five agents and the Pub/Sub routing between them:

    Cloud Scheduler ──> run_sentinel_cycle()
                            │  aushadhi-sentinel-alerts
                            ▼
    sentinel-alerts-sub ──> DQMSValidationAgent
                            │  aushadhi-validated-data
                            ▼
    validated-data-sub ───> ForecastOutbreakAgent   (both Gemini calls)
                            │  aushadhi-forecast-complete
                            ▼
    forecast-complete-sub ─> ProcurementAgent
                            │  aushadhi-procured
                            ▼
    procured-sub ─────────> AlertReportAgent

start_subscribers() runs the four pull loops concurrently under
asyncio.gather. Each loop is independent: one agent raising does not stop the
others, and a raised handler nacks its message for redelivery instead of
losing it.
"""

import asyncio
import time
from functools import lru_cache
from typing import Any, Dict, List, Optional

from services.firestore_service import FirestoreService, get_firestore_service
from services.pubsub_service import PubSubService, get_pubsub_service
from utils.logger import get_logger

from agents.alert_agent import AlertReportAgent
from agents.base_agent import BaseAgent
from agents.dqms_agent import DQMSValidationAgent
from agents.forecast_agent import ForecastOutbreakAgent
from agents.procurement_agent import ProcurementAgent
from agents.sentinel_agent import InventorySentinelAgent

log = get_logger(__name__)

#: Messages pulled per subscriber iteration.
PULL_BATCH_SIZE = 10
#: Long-poll timeout for one pull.
PULL_TIMEOUT_SECONDS = 20.0
#: Pause between empty pulls, so an idle pipeline does not spin.
IDLE_SLEEP_SECONDS = 1.0
#: Backoff after a subscriber loop error, so a broken loop does not hot-spin.
ERROR_SLEEP_SECONDS = 5.0


class AushadhiOrchestrator:
    """Manages all 5 agents and their Pub/Sub routing."""

    def __init__(
        self,
        firestore: Optional[FirestoreService] = None,
        pubsub: Optional[PubSubService] = None,
    ) -> None:
        self.firestore = firestore or get_firestore_service()
        self.pubsub = pubsub or get_pubsub_service()

        self.sentinel_agent = InventorySentinelAgent(self.firestore, self.pubsub)
        self.dqms_agent = DQMSValidationAgent(self.firestore, self.pubsub)
        self.forecast_agent = ForecastOutbreakAgent(self.firestore, self.pubsub)
        self.procurement_agent = ProcurementAgent(self.firestore, self.pubsub)
        self.alert_agent = AlertReportAgent(self.firestore, self.pubsub)

        #: subscription short name -> agent consuming it
        self.subscriptions: Dict[str, BaseAgent] = {
            "sentinel-alerts-sub": self.dqms_agent,
            "validated-data-sub": self.forecast_agent,
            "forecast-complete-sub": self.procurement_agent,
            "procured-sub": self.alert_agent,
        }

        self._running = False
        self._tasks: List[asyncio.Task] = []
        self._last_activity = time.monotonic()
        self._messages_handled = 0
        # Handlers currently running. A long Gemini call (rate limiter +
        # retry backoff) handles no new messages for minutes, so message
        # counts alone would read as idle while work is still in flight.
        self._inflight = 0

    # ─────────────────────────── scheduler entry ───────────────────────

    async def run_sentinel_cycle(
        self, district: Optional[str] = None, cycle_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Called by Cloud Scheduler every 30 minutes."""
        log.info("orchestrator_sentinel_cycle_start", district=district or "ALL")
        result = await self.sentinel_agent.scan_all_centers(
            district=district, cycle_id=cycle_id
        )
        self._mark_activity()
        log.info(
            "orchestrator_sentinel_cycle_done",
            cycle_id=result.get("cycle_id"),
            centers_alerting=result.get("centers_alerting"),
        )
        return result

    # ───────────────────────────── subscribers ─────────────────────────

    async def start_subscribers(self) -> None:
        """Start all Pub/Sub subscribers and block until stop() is called."""
        self._running = True
        self._mark_activity()
        log.info("orchestrator_subscribers_starting", subscriptions=list(self.subscriptions))

        self._tasks = [
            asyncio.create_task(self._subscribe(subscription, agent), name=f"sub:{subscription}")
            for subscription, agent in self.subscriptions.items()
        ]
        try:
            await asyncio.gather(*self._tasks)
        except asyncio.CancelledError:
            log.info("orchestrator_subscribers_cancelled")
            raise
        finally:
            self._running = False

    async def _subscribe(self, subscription: str, agent: BaseAgent) -> None:
        """One pull loop for one subscription."""
        log.info("subscriber_started", subscription=subscription, agent=agent.name)
        while self._running:
            try:
                handled = await self.pubsub.subscribe(
                    subscription,
                    self._tracked(agent),
                    max_messages=PULL_BATCH_SIZE,
                    timeout=PULL_TIMEOUT_SECONDS,
                )
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                log.error(
                    "subscriber_loop_error",
                    subscription=subscription,
                    agent=agent.name,
                    error_type=type(exc).__name__,
                    error=str(exc),
                )
                await asyncio.sleep(ERROR_SLEEP_SECONDS)
                continue

            if handled:
                self._messages_handled += handled
                self._mark_activity()
            else:
                await asyncio.sleep(IDLE_SLEEP_SECONDS)

        log.info("subscriber_stopped", subscription=subscription, agent=agent.name)

    def _tracked(self, agent: BaseAgent):
        """Wrap a handler so in-flight work keeps the pipeline from reading idle."""

        async def handler(message: Dict[str, Any]) -> None:
            self._inflight += 1
            self._mark_activity()
            try:
                await agent.handle_message(message)
            finally:
                self._inflight -= 1
                self._mark_activity()

        return handler

    async def stop(self) -> None:
        """Stop the subscriber loops and release clients."""
        self._running = False
        for task in self._tasks:
            task.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks = []
        log.info("orchestrator_stopped", messages_handled=self._messages_handled)

    # ────────────────────────────── idle state ─────────────────────────
    # A cycle is "done" when nothing has moved for a while — used by the
    # end-to-end test to know when to stop watching.

    def _mark_activity(self) -> None:
        self._last_activity = time.monotonic()

    @property
    def seconds_since_activity(self) -> float:
        return time.monotonic() - self._last_activity

    @property
    def messages_handled(self) -> int:
        return self._messages_handled

    @property
    def inflight(self) -> int:
        return self._inflight

    async def wait_until_idle(
        self, idle_seconds: float = 30.0, timeout_seconds: float = 600.0
    ) -> bool:
        """Block until no agent has handled a message for `idle_seconds`.

        Returns True if the pipeline went quiet, False if `timeout_seconds`
        elapsed first. Any district still buffered in the Forecast Agent is
        flushed before the pipeline is declared idle.
        """
        deadline = time.monotonic() + timeout_seconds
        flushed = False
        while time.monotonic() < deadline:
            if self._inflight == 0 and self.seconds_since_activity >= idle_seconds:
                if not flushed:
                    # A district that lost a message would otherwise sit in the
                    # buffer forever; analyse it, then keep watching.
                    pending = await self.forecast_agent.flush_pending()
                    flushed = True
                    if pending:
                        self._mark_activity()
                        continue
                return True
            await asyncio.sleep(1.0)
        return False


@lru_cache
def get_orchestrator() -> AushadhiOrchestrator:
    """Process-wide orchestrator, shared by the API routes and the agent runner."""
    return AushadhiOrchestrator()
