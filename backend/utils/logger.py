"""AUSHADHI — structlog configuration.

Development: coloured console output.
Production:  JSON lines (Cloud Logging picks these up from stdout).

Usage:
    from utils.logger import get_logger
    log = get_logger(__name__)
    log.info("sentinel_poll_started", center_id="phc_razole_001")
"""

import logging
import sys

import structlog

from config import settings

_configured = False


def configure_logging() -> None:
    """Configure stdlib logging + structlog. Safe to call more than once."""
    global _configured
    if _configured:
        return

    level = getattr(logging, settings.log_level, logging.INFO)

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=level,
        force=True,
    )
    for noisy in ("uvicorn.access", "google", "urllib3"):
        logging.getLogger(noisy).setLevel(max(level, logging.WARNING))

    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    if settings.environment == "development":
        processors += [
            structlog.processors.format_exc_info,
            structlog.dev.ConsoleRenderer(colors=True),
        ]
    else:
        processors += [
            structlog.processors.dict_tracebacks,
            structlog.processors.EventRenamer("message"),
            structlog.processors.JSONRenderer(),
        ]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(level),
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )

    _configured = True


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Return a bound structlog logger, configuring logging on first use."""
    configure_logging()
    return structlog.get_logger().bind(logger=name or settings.app_name)
