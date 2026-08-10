"""Configuration is read from the environment only (12-factor style).

Keeping every tunable in one dataclass makes it obvious what has to be
supplied as a ConfigMap or Secret once we move to Kubernetes.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

DEFAULT_DATABASE_URL = "postgresql+psycopg://sentinel:sentinel@localhost:5432/sentinel"
DEFAULT_REDIS_URL = "redis://localhost:6379/0"


@dataclass(frozen=True)
class Settings:
    """Immutable runtime settings."""

    database_url: str
    redis_url: str
    queue_key: str
    probe_timeout_seconds: float
    scheduler_interval_seconds: float
    worker_block_timeout_seconds: int
    log_level: str


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return float(raw)
    except ValueError as exc:  # fail fast rather than silently mis-configuring
        raise ValueError(f"{name} must be a number, got {raw!r}") from exc


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer, got {raw!r}") from exc


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Build settings once per process."""
    return Settings(
        database_url=os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL),
        redis_url=os.getenv("REDIS_URL", DEFAULT_REDIS_URL),
        queue_key=os.getenv("QUEUE_KEY", "sentinel:checks"),
        probe_timeout_seconds=_env_float("PROBE_TIMEOUT_SECONDS", 10.0),
        scheduler_interval_seconds=_env_float("SCHEDULER_INTERVAL_SECONDS", 5.0),
        worker_block_timeout_seconds=_env_int("WORKER_BLOCK_TIMEOUT_SECONDS", 5),
        log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
    )
