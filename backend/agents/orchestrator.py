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
#: Ceiling on how long shutdown waits for in-flight handlers to unwind.
SHUTDOWN_TIMEOUT_SECONDS = 5.0
#: How often to sweep district buffers that are waiting on a message that
#: never came. Without this a stalled buffer never resolves.
BUFFER_SWEEP_SECONDS = 20.0


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
        self._background_task: Optional[asyncio.Task] = None
        self._started_at: Optional[float] = None
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

    # ─────────────────────────── background runner ─────────────────────

    def start_background(self) -> asyncio.Task:
        """Run the subscriber loops as a task owned by this orchestrator.

        Called from the API's lifespan so one `uvicorn main:app` starts the
        agents too. Idempotent: a second call returns the running task rather
        than opening a second set of subscribers.
        """
        if self._background_task is not None and not self._background_task.done():
            return self._background_task

        self._started_at = time.time()
        self._background_task = asyncio.create_task(
            self.start_subscribers(), name="agent-orchestrator"
        )
        log.info("agent_orchestrator_started", subscriptions=list(self.subscriptions))
        return self._background_task

    async def stop_background(self) -> None:
        """Cancel the background task and release the subscriber loops."""
        await self.stop()
        task = self._background_task
        self._background_task = None
        if task is None:
            return
        task.cancel()
        try:
            await asyncio.wait_for(task, timeout=SHUTDOWN_TIMEOUT_SECONDS)
        except (asyncio.CancelledError, asyncio.TimeoutError):
            pass
        except Exception as exc:
            log.warning(
                "agent_orchestrator_stop_error",
                error_type=type(exc).__name__,
                error=str(exc),
            )
        log.info("agent_orchestrator_stopped", messages_handled=self._messages_handled)

    @property
    def background_status(self) -> Dict[str, Any]:
        """Snapshot for GET /api/v1/agents/orchestrator-status."""
        task = self._background_task
        running = bool(task is not None and not task.done())

        failure: Optional[str] = None
        if task is not None and task.done() and not task.cancelled():
            exc = task.exception()
            if exc is not None:
                failure = f"{type(exc).__name__}: {exc}"

        return {
            "running": running,
            # Healthy means the loops are up and none of them died with an error.
            "healthy": running and failure is None,
            "state": "running" if running else ("stopped" if task is not None else "not_started"),
            "subscriptions": list(self.subscriptions),
            "subscriber_loops": len(self._tasks),
            "agents": [agent.name for agent in self.subscriptions.values()],
            "messages_handled": self._messages_handled,
            "in_flight": self._inflight,
            "seconds_since_activity": round(self.seconds_since_activity, 1),
            "uptime_seconds": round(time.time() - self._started_at, 1) if self._started_at else None,
            "error": failure,
        }

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
        self._tasks.append(asyncio.create_task(self._sweep_buffers(), name="buffer-sweeper"))

        log.info(
            "orchestrator_all_tasks_created",
            task_count=len(self._tasks),
            task_names=[t.get_name() for t in self._tasks],
        )

        # Blocks here until every loop stops or the gather is cancelled.
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

    async def _sweep_buffers(self) -> None:
        """Timer that resolves district buffers stuck waiting for a late message."""
        while self._running:
            await asyncio.sleep(BUFFER_SWEEP_SECONDS)
            try:
                flushed = await self.forecast_agent.flush_stale()
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                log.error(
                    "buffer_sweep_failed", error_type=type(exc).__name__, error=str(exc)
                )
                continue
            if flushed:
                self._mark_activity()
                log.info("buffer_sweep_flushed", districts=len(flushed))

    async def stop(self) -> None:
        """Stop the subscriber loops and release clients."""
        self._running = False
        for task in self._tasks:
            task.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks = []
        log.info("orchestrator_stopped", messages_handled=self._messages_handled)

    async def close(self) -> None:
        """Release the Firestore and Pub/Sub gRPC clients.

        Their channels run non-daemon threads, so a standalone worker will not
        exit after shutdown unless they are closed explicitly.
        """
        try:
            self.pubsub.close()
        except Exception as exc:
            log.warning("pubsub_close_failed", error_type=type(exc).__name__, error=str(exc))
        try:
            await self.firestore.close()
        except Exception as exc:
            log.warning("firestore_close_failed", error_type=type(exc).__name__, error=str(exc))
        log.info("orchestrator_clients_closed")

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


if __name__ == "__main__":
    # Standalone worker:  cd backend && python3 -m agents.orchestrator
    #
    # Only needed when running the agents apart from the API (separate Cloud Run
    # service, or AGENTS_IN_PROCESS=false). The default deployment starts these
    # same loops inside `uvicorn main:app`, so one process runs everything.
    import signal

    async def _main() -> None:
        orchestrator = get_orchestrator()
        stop_event = asyncio.Event()

        def handle_signal() -> None:
            log.info("orchestrator_stopping")
            stop_event.set()

        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            try:
                loop.add_signal_handler(sig, handle_signal)
            except NotImplementedError:
                # Windows event loops have no signal handler support.
                signal.signal(sig, lambda *_: handle_signal())

        subscriber_task = orchestrator.start_background()
        log.info(
            "orchestrator_started",
            subscriptions=list(orchestrator.subscriptions),
            agents=[agent.name for agent in orchestrator.subscriptions.values()],
        )

        log.info("orchestrator_running_waiting_for_messages")

        # Block here until SIGINT/SIGTERM, or until the loops die on their own.
        stopper = asyncio.create_task(stop_event.wait(), name="stop-signal")
        done, _pending = await asyncio.wait(
            {stopper, subscriber_task}, return_when=asyncio.FIRST_COMPLETED
        )
        if subscriber_task in done and not subscriber_task.cancelled():
            exc = subscriber_task.exception()
            if exc is not None:
                log.error(
                    "orchestrator_subscribers_crashed",
                    error_type=type(exc).__name__,
                    error=str(exc),
                )
        stopper.cancel()

        await orchestrator.stop_background()
        await orchestrator.close()
        log.info("orchestrator_stopped")

    asyncio.run(_main())
