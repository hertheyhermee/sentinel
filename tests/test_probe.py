"""Probe tests.

``httpx.MockTransport`` lets us assert on real client behaviour without any
network access, so these tests are fast and cannot flake in CI.
"""

from __future__ import annotations

import httpx

from sentinel_core.probe import execute_probe


def _client(handler: object) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))  # type: ignore[arg-type]


def test_matching_status_is_up() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="ok")

    with _client(handler) as client:
        outcome = execute_probe("https://example.com", client=client)

    assert outcome.is_up is True
    assert outcome.status_code == 200
    assert outcome.error is None
    assert outcome.response_time_ms is not None


def test_unexpected_status_is_down_with_reason() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(500)

    with _client(handler) as client:
        outcome = execute_probe("https://example.com", client=client)

    assert outcome.is_up is False
    assert outcome.status_code == 500
    assert outcome.error is not None
    assert "500" in outcome.error


def test_custom_expected_status() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(204)

    with _client(handler) as client:
        outcome = execute_probe(
            "https://example.com", expected_status=204, client=client
        )

    assert outcome.is_up is True


def test_timeout_is_recorded_not_raised() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("too slow", request=request)

    with _client(handler) as client:
        outcome = execute_probe(
            "https://example.com", timeout_seconds=1.0, client=client
        )

    assert outcome.is_up is False
    assert outcome.status_code is None
    assert outcome.error is not None
    assert "timeout" in outcome.error


def test_connection_error_is_recorded_not_raised() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    with _client(handler) as client:
        outcome = execute_probe("https://example.com", client=client)

    assert outcome.is_up is False
    assert outcome.status_code is None
    assert outcome.error is not None
    assert "ConnectError" in outcome.error


def test_method_is_passed_through() -> None:
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.method)
        return httpx.Response(200)

    with _client(handler) as client:
        execute_probe("https://example.com", method="head", client=client)

    assert seen == ["HEAD"]


def test_duration_seconds_converts_from_milliseconds() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200)

    with _client(handler) as client:
        outcome = execute_probe("https://example.com", client=client)

    assert outcome.duration_seconds == (outcome.response_time_ms or 0) / 1000.0
