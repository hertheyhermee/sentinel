"""Scheduler: finds monitors that are due and enqueues one probe job each.

The interesting engineering detail is the claim query. It uses
``SELECT ... FOR UPDATE SKIP LOCKED`` and advances ``next_run_at`` in the same
transaction. That makes the scheduler safe to run as more than one replica:
two schedulers cannot hand out the same monitor in the same tick, because the
row is locked and the second scheduler skips it rather than blocking.

Without SKIP LOCKED you get either duplicate probes (no locking) or schedulers
serialising behind each other (plain FOR UPDATE).
"""

from __future__ import annotations

import signal
import sys
import threading
from datetime import timedelta

from prometheus_client import start_http_server
from sqlalchemy import select

from sentinel_core import queue
from sentinel_core.config import get_settings
from sentinel_core.db import session_scope
from sentinel_core.logging_config import configure_logging
from sentinel_core.metrics import (
    CHECKS_ENQUEUED_TOTAL,
    QUEUE_DEPTH,
    SCHEDULER_LOOP_SECONDS,
)
from sentinel_core.models import Monitor, utcnow

METRICS_PORT = 9100
BATCH_SIZE = 100

settings = get_settings()
logger = configure_logging("scheduler", settings.log_level)

_shutdown = threading.Event()


def _handle_signal(signum: int, _frame: object) -> None:
    """Exit cleanly so Kubernetes rolling updates do not lose a tick."""
    logger.info("shutdown signal received", extra={"signal": signum})
    _shutdown.set()


def claim_due_monitors(limit: int = BATCH_SIZE) -> list[int]:
    """Atomically claim due monitors and reschedule them.

    Returns the ids that this scheduler instance is responsible for enqueueing.
    """
    claimed: list[int] = []

    with session_scope() as session:
        now = utcnow()
        stmt = (
            select(Monitor)
            .where(Monitor.is_active.is_(True), Monitor.next_run_at <= now)
            .order_by(Monitor.next_run_at)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )

        for monitor in session.scalars(stmt):
            claimed.append(monitor.id)
            # Advance the clock immediately; the commit releases the lock.
            monitor.next_run_at = now + timedelta(seconds=monitor.interval_seconds)

    return claimed


def tick() -> int:
    """One scheduling pass. Returns how many jobs were enqueued."""
    with SCHEDULER_LOOP_SECONDS.time():
        monitor_ids = claim_due_monitors()

        for monitor_id in monitor_ids:
            queue.enqueue_check(monitor_id)
            CHECKS_ENQUEUED_TOTAL.inc()

        try:
            QUEUE_DEPTH.set(queue.queue_depth())
        except Exception as exc:
            logger.warning("could not read queue depth", extra={"error": str(exc)})

        if monitor_ids:
            logger.info(
                "enqueued due checks",
                extra={"count": len(monitor_ids), "monitor_ids": monitor_ids},
            )

        return len(monitor_ids)


def main() -> int:
    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    start_http_server(METRICS_PORT)
    logger.info(
        "scheduler started",
        extra={
            "interval_seconds": settings.scheduler_interval_seconds,
            "metrics_port": METRICS_PORT,
        },
    )

    while not _shutdown.is_set():
        try:
            tick()
        except Exception as exc:
            # Never let one bad tick kill the loop; log and retry next interval.
            logger.error(
                "scheduler tick failed", extra={"error": str(exc)}, exc_info=True
            )

        _shutdown.wait(timeout=settings.scheduler_interval_seconds)

    logger.info("scheduler stopped")
    return 0


if __name__ == "__main__":
    sys.exit(main())
