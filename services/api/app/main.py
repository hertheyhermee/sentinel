"""API entrypoint.

Note the deliberate split between liveness and readiness. Kubernetes treats
them very differently:

* ``/health`` (liveness) must not touch dependencies. If it checked Postgres,
  a brief database blip would make the kubelet restart every pod, turning a
  recoverable dependency issue into a full outage.
* ``/ready`` (readiness) does check dependencies, so a pod is removed from the
  Service endpoints while it cannot serve traffic, then added back on recovery.
"""

from __future__ import annotations

from fastapi import FastAPI, Response, status
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from sqlalchemy import text

from sentinel_core import queue
from sentinel_core.config import get_settings
from sentinel_core.db import get_engine
from sentinel_core.logging_config import configure_logging
from sentinel_core.metrics import QUEUE_DEPTH

from .routers import router as monitors_router
from .schemas import HealthRead

settings = get_settings()
logger = configure_logging("api", settings.log_level)

app = FastAPI(
    title="Sentinel",
    description="Uptime and SLO monitoring platform.",
    version="0.1.0",
)

app.include_router(monitors_router)


@app.get("/health", response_model=HealthRead, tags=["ops"])
def health() -> HealthRead:
    """Liveness: is this process alive? No dependency checks on purpose."""
    return HealthRead(status="ok", checks={"process": "ok"})


@app.get("/ready", response_model=HealthRead, tags=["ops"])
def ready(response: Response) -> HealthRead:
    """Readiness: can this process actually serve requests right now?"""
    checks: dict[str, str] = {}

    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as exc:
        logger.warning("readiness database check failed", extra={"error": str(exc)})
        checks["database"] = "error"

    checks["redis"] = "ok" if queue.ping() else "error"

    healthy = all(value == "ok" for value in checks.values())
    if not healthy:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return HealthRead(status="ok" if healthy else "degraded", checks=checks)


@app.get("/metrics", tags=["ops"])
def metrics() -> Response:
    """Prometheus scrape endpoint.

    Queue depth is refreshed at scrape time because the API is not the process
    that mutates the queue; reading it here keeps the gauge honest.
    """
    try:
        QUEUE_DEPTH.set(queue.queue_depth())
    except Exception as exc:  # a metrics failure must never break the endpoint
        logger.warning("could not read queue depth", extra={"error": str(exc)})

    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/", tags=["ops"])
def root() -> dict[str, str]:
    return {
        "service": "sentinel-api",
        "version": "0.1.0",
        "docs": "/docs",
        "metrics": "/metrics",
    }
