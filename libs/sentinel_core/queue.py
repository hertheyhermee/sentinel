"""A deliberately simple Redis list queue.

Why a raw Redis list instead of Celery or RQ:

* ``LLEN`` gives a single integer that represents backlog. That is exactly the
  custom metric we will autoscale probe workers on with a Kubernetes HPA later,
  and it is easy to explain in an interview.
* ``BLPOP`` blocks, so idle workers consume no CPU.

Trade-off worth knowing: this is at-most-once delivery. If a worker crashes
between popping and writing the result, that probe is simply skipped and the
next scheduled run covers it. For uptime sampling that is acceptable; for money
movement it would not be.
"""

from __future__ import annotations

import json

import redis

from .config import get_settings

_client: redis.Redis | None = None


def get_client() -> redis.Redis:
    """Process-wide Redis client."""
    global _client
    if _client is None:
        settings = get_settings()
        _client = redis.Redis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_keepalive=True,
            health_check_interval=30,
        )
    return _client


def enqueue_check(monitor_id: int) -> None:
    """Push one probe job onto the tail of the queue."""
    settings = get_settings()
    payload = json.dumps({"monitor_id": monitor_id})
    get_client().rpush(settings.queue_key, payload)


def dequeue_check(timeout: int) -> int | None:
    """Block until a job arrives, returning its monitor id.

    Returns ``None`` when the timeout expires so the caller can run periodic
    work (metrics refresh, shutdown checks) between jobs.
    """
    settings = get_settings()
    item = get_client().blpop([settings.queue_key], timeout=timeout)
    if item is None:
        return None

    _key, raw = item
    try:
        return int(json.loads(raw)["monitor_id"])
    except (ValueError, KeyError, TypeError, json.JSONDecodeError):
        # Malformed payloads are dropped rather than crash-looping the worker.
        return None


def queue_depth() -> int:
    """Current backlog. Exported as a metric and used as the HPA signal."""
    settings = get_settings()
    return int(get_client().llen(settings.queue_key))


def ping() -> bool:
    """Used by readiness probes."""
    try:
        return bool(get_client().ping())
    except redis.RedisError:
        return False
