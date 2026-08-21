"""AUSHADHI — Pub/Sub messaging layer.

Every agent hand-off in the pipeline goes through this service:

    sentinel  --> aushadhi-sentinel-alerts    --> dqms
    dqms      --> aushadhi-validated-data     --> forecast
    forecast  --> aushadhi-forecast-complete  --> procurement / alert
    procurement --> aushadhi-procured         --> alert

Topic and subscription short names are expanded with settings.topic(), so
callers pass "sentinel-alerts" / "sentinel-alerts-sub" and never the
"aushadhi-" prefix or the full projects/.../topics/... path.

The google-cloud-pubsub clients are synchronous, so every blocking call is
pushed onto a worker thread with asyncio.to_thread() — that keeps the agents'
event loop free while a publish or pull is in flight.
"""

import asyncio
import inspect
import json
import time
from functools import lru_cache
from typing import Any, Awaitable, Callable, Dict, List, Optional, Union

from google.cloud import pubsub_v1

from config import settings
from utils.logger import get_logger
from utils.retry import retry

log = get_logger(__name__)

# Pub/Sub transient failures (503 UNAVAILABLE) clear quickly — much faster than
# Gemini overload — so this uses a shorter backoff than the decorator defaults.
pubsub_retry = retry(max_attempts=3, initial_delay=1.0, backoff_factor=2.0, max_delay=8.0)

MessageCallback = Callable[[Dict[str, Any]], Union[None, Awaitable[None]]]

DEFAULT_MAX_MESSAGES = 10
DEFAULT_PULL_TIMEOUT_SECONDS = 30.0
#: Ack deadline granted to a pulled batch. The Forecast Agent can hold a
#: message for minutes (Gemini rate limiting plus 503 backoff), and the
#: subscriptions are created with a 120s deadline — without this extension
#: Pub/Sub would redeliver mid-processing and duplicate the Gemini calls.
LEASE_EXTENSION_SECONDS = 600


class PubSubService:
    """Async wrapper over Pub/Sub publish + pull for the AUSHADHI agent pipeline."""

    def __init__(
        self,
        publisher: Optional[pubsub_v1.PublisherClient] = None,
        subscriber: Optional[pubsub_v1.SubscriberClient] = None,
    ) -> None:
        self._publisher = publisher or pubsub_v1.PublisherClient()
        self._subscriber = subscriber or pubsub_v1.SubscriberClient()
        self._project = settings.google_cloud_project
        log.info(
            "pubsub_service_initialized",
            project=self._project,
            topic_prefix=settings.pubsub_topic_prefix,
        )

    # ───────────────────────── name resolution ─────────────────────────

    def topic_path(self, topic_name: str) -> str:
        """Full topic path for a short name ("sentinel-alerts")."""
        if topic_name.startswith("projects/"):
            return topic_name
        return self._publisher.topic_path(self._project, settings.topic(topic_name))

    def subscription_path(self, subscription_name: str) -> str:
        """Full subscription path for a short name ("sentinel-alerts-sub")."""
        if subscription_name.startswith("projects/"):
            return subscription_name
        return self._subscriber.subscription_path(
            self._project, settings.topic(subscription_name)
        )

    # ───────────────────────────── PUBLISH ─────────────────────────────

    @pubsub_retry
    async def publish(
        self,
        topic_name: str,
        message_dict: Dict[str, Any],
        **attributes: str,
    ) -> str:
        """JSON-encode message_dict, publish it to topic_name, return the message_id."""
        path = self.topic_path(topic_name)
        payload = json.dumps(message_dict, default=str).encode("utf-8")

        started = time.perf_counter()
        future = self._publisher.publish(path, payload, **attributes)
        message_id = await asyncio.to_thread(future.result)
        duration_ms = int((time.perf_counter() - started) * 1000)

        log.info(
            "pubsub_published",
            topic=path,
            message_id=message_id,
            payload_bytes=len(payload),
            duration_ms=duration_ms,
        )
        return message_id

    # ──────────────────────────── SUBSCRIBE ────────────────────────────

    @pubsub_retry
    async def subscribe(
        self,
        subscription_name: str,
        callback: MessageCallback,
        max_messages: int = DEFAULT_MAX_MESSAGES,
        timeout: float = DEFAULT_PULL_TIMEOUT_SECONDS,
    ) -> int:
        """Pull up to max_messages, run callback(message_dict) on each, ack/nack.

        The callback may be sync or async. A message is acked when the callback
        returns cleanly and nacked (redelivered) when it raises, so a crashing
        agent never silently drops work. Returns the number of acked messages.
        """
        path = self.subscription_path(subscription_name)

        started = time.perf_counter()
        response = await asyncio.to_thread(
            self._subscriber.pull,
            request={"subscription": path, "max_messages": max_messages},
            timeout=timeout,
        )
        pull_ms = int((time.perf_counter() - started) * 1000)

        received = list(response.received_messages)
        if not received:
            log.debug("pubsub_pull_empty", subscription=path, duration_ms=pull_ms)
            return 0

        log.info(
            "pubsub_pulled",
            subscription=path,
            message_count=len(received),
            duration_ms=pull_ms,
        )

        try:
            await asyncio.to_thread(
                self._subscriber.modify_ack_deadline,
                request={
                    "subscription": path,
                    "ack_ids": [m.ack_id for m in received],
                    "ack_deadline_seconds": LEASE_EXTENSION_SECONDS,
                },
            )
        except Exception as exc:
            # Not fatal: the batch still processes, it just risks redelivery.
            log.warning(
                "pubsub_lease_extension_failed",
                subscription=path,
                error_type=type(exc).__name__,
                error=str(exc),
            )

        ack_ids: List[str] = []
        nack_ids: List[str] = []

        for received_message in received:
            message = received_message.message
            message_id = message.message_id
            handled = time.perf_counter()
            try:
                message_dict = json.loads(message.data.decode("utf-8"))
                result = callback(message_dict)
                if inspect.isawaitable(result):
                    await result
            except Exception as exc:
                nack_ids.append(received_message.ack_id)
                log.error(
                    "pubsub_message_failed",
                    subscription=path,
                    message_id=message_id,
                    duration_ms=int((time.perf_counter() - handled) * 1000),
                    error_type=type(exc).__name__,
                    error=str(exc),
                )
            else:
                ack_ids.append(received_message.ack_id)
                log.info(
                    "pubsub_message_handled",
                    subscription=path,
                    message_id=message_id,
                    duration_ms=int((time.perf_counter() - handled) * 1000),
                )

        if ack_ids:
            await asyncio.to_thread(
                self._subscriber.acknowledge,
                request={"subscription": path, "ack_ids": ack_ids},
            )
        if nack_ids:
            # ack_deadline_seconds=0 makes Pub/Sub redeliver immediately.
            await asyncio.to_thread(
                self._subscriber.modify_ack_deadline,
                request={
                    "subscription": path,
                    "ack_ids": nack_ids,
                    "ack_deadline_seconds": 0,
                },
            )

        log.info(
            "pubsub_pull_complete",
            subscription=path,
            acked=len(ack_ids),
            nacked=len(nack_ids),
            duration_ms=int((time.perf_counter() - started) * 1000),
        )
        return len(ack_ids)

    # ──────────────────────────────── HEALTH ───────────────────────────

    async def list_topics(self, timeout: float = 10.0) -> List[str]:
        """Topic names in the project — used by /health to prove connectivity.

        `timeout` is passed to gRPC as a deadline: without one the call can hang
        forever on a wedged channel and take the health check down with it.
        """
        project_path = f"projects/{self._project}"
        topics = await asyncio.to_thread(
            lambda: list(
                self._publisher.list_topics(
                    request={"project": project_path}, timeout=timeout
                )
            )
        )
        return [topic.name.rsplit("/", 1)[-1] for topic in topics]

    # ────────────────────────────── LIFECYCLE ──────────────────────────

    def close(self) -> None:
        """Release the subscriber's gRPC channel (publisher has no close())."""
        self._subscriber.close()
        log.info("pubsub_service_closed", project=self._project)


@lru_cache
def get_pubsub_service() -> PubSubService:
    """Process-wide PubSubService singleton."""
    return PubSubService()
