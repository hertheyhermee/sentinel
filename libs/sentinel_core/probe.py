"""The actual availability check.

Isolated from the worker loop so it can be unit tested against a stub transport
with no network access, which keeps CI fast and deterministic.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

import httpx


@dataclass(frozen=True)
class ProbeOutcome:
    """Result of a single HTTP probe."""

    is_up: bool
    status_code: int | None
    response_time_ms: float | None
    error: str | None

    @property
    def duration_seconds(self) -> float:
        """Duration in seconds for the Prometheus histogram."""
        return (self.response_time_ms or 0.0) / 1000.0


def execute_probe(
    url: str,
    method: str = "GET",
    expected_status: int = 200,
    timeout_seconds: float = 10.0,
    client: httpx.Client | None = None,
) -> ProbeOutcome:
    """Probe ``url`` once and classify the result.

    Never raises for network conditions. A DNS failure, refused connection or
    timeout is data, not an exception, so it is recorded as a down sample.
    """
    owns_client = client is None
    if client is None:
        client = httpx.Client(timeout=timeout_seconds, follow_redirects=True)

    started = time.perf_counter()
    try:
        response = client.request(method.upper(), url)
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        return ProbeOutcome(
            is_up=response.status_code == expected_status,
            status_code=response.status_code,
            response_time_ms=round(elapsed_ms, 2),
            error=(
                None
                if response.status_code == expected_status
                else f"expected status {expected_status}, got {response.status_code}"
            ),
        )
    except httpx.TimeoutException:
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        return ProbeOutcome(
            is_up=False,
            status_code=None,
            response_time_ms=round(elapsed_ms, 2),
            error=f"timeout after {timeout_seconds}s",
        )
    except httpx.HTTPError as exc:
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        return ProbeOutcome(
            is_up=False,
            status_code=None,
            response_time_ms=round(elapsed_ms, 2),
            error=f"{type(exc).__name__}: {exc}",
        )
    finally:
        if owns_client:
            client.close()
