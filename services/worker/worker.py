"""Worker: consumes probe jobs, executes the HTTP check, records the result.

This is the horizontally scalable component. Queue depth is the natural
autoscaling signal, so in Phase 3 a Kubernetes HPA scales replicas on
``sentinel_queue_depth`` rather than on CPU, which barely moves for an
IO-bound workload like this.

A single ``httpx.Client`` is reused for the process lifetime so connections are
pooled across probes instead of paying TCP and TLS setup on every check.
"""

from __future__ import annotations

import signal
import sys
import threading

import httpx
from prometheus_client import start_http_server

from sentinel_core import queue
from sentinel_core.config import get_settings
from sentinel_core.db import session_scope
from sentinel_core.logging_config import configure_logging
from sentinel_core.metrics import (
    PROBE_DURATION_SECONDS,
    PROBE_UP,
    PROBES_TOTAL,
    QUEUE_DEPTH,
)
from sentinel_core.models import CheckResult, Monitor
from sentinel_core.probe import execute_probe

METRICS_PORT = 9101

settings = get_settings()
logger = configure_logging("worker", settings.log_level)

_shutdown = threading.Event()


def _handle_signal(signum: int, _frame: object) -> None:
    """Finish the in-flight probe, then stop. Avoids losing a sample mid-check."""
    logger.info("shutdown signal received", extra={"signal": signum})
    _shutdown.set()


def process_check(monitor_id: int, client: httpx.Client) -> None:
    """Probe one monitor and persist the outcome."""
    with session_scope() as session:
        monitor = session.get(Monitor, monitor_id)

        if monitor is None:
            # Deleted between enqueue and dequeue. Normal, not an error.
            logger.info("monitor no longer exists", extra={"monitor_id": monitor_id})
            return

        if not monitor.is_active:
            logger.info("monitor is paused", extra={"monitor_id": monitor_id})
            return

        outcome = execute_probe(
            url=monitor.url,
            method=monitor.method,
            expected_status=monitor.expected_status,
            timeout_seconds=settings.probe_timeout_seconds,
            client=client,
        )

        session.add(
            CheckResult(
                monitor_id=monitor.id,
                status_code=outcome.status_code,
                response_time_ms=outcome.response_time_ms,
                is_up=outcome.is_up,
                error=outcome.error,
            )
        )

        label = str(monitor.id)
        PROBES_TOTAL.labels(
            monitor_id=label, outcome="up" if outcome.is_up else "down"
        ).inc()
        PROBE_DURATION_SECONDS.labels(monitor_id=label).observe(
            outcome.duration_seconds
        )
        PROBE_UP.labels(monitor_id=label).set(1 if outcome.is_up else 0)

        logger.info(
            "probe completed",
            extra={
                "monitor_id": monitor.id,
                "url": monitor.url,
                "is_up": outcome.is_up,
                "status_code": outcome.status_code,
                "response_time_ms": outcome.response_time_ms,
                "error": outcome.error,
            },
        )


def main() -> int:
    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    start_http_server(METRICS_PORT)
    logger.info("worker started", extra={"metrics_port": METRICS_PORT})

    client = httpx.Client(
        timeout=settings.probe_timeout_seconds,
        follow_redirects=True,
        limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
    )

    try:
        while not _shutdown.is_set():
            try:
                monitor_id = queue.dequeue_check(
                    timeout=settings.worker_block_timeout_seconds
                )

                # Timeout with an empty queue: refresh the gauge and loop.
                if monitor_id is None:
                    QUEUE_DEPTH.set(queue.queue_depth())
                    continue

                process_check(monitor_id, client)
                QUEUE_DEPTH.set(queue.queue_depth())

            except Exception as exc:
                # A failure on one job must not take down the worker.
                logger.error(
                    "failed to process check", extra={"error": str(exc)}, exc_info=True
                )
                _shutdown.wait(timeout=1.0)
    finally:
        client.close()

    logger.info("worker stopped")
    return 0


if __name__ == "__main__":
    sys.exit(main())
