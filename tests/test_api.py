"""API tests."""

from __future__ import annotations

from datetime import timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from sentinel_core.models import CheckResult, Monitor, utcnow

VALID_MONITOR = {
    "name": "example",
    "url": "https://example.com",
    "interval_seconds": 60,
}


class TestHealth:
    def test_liveness_is_always_ok(self, client: TestClient) -> None:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_root_advertises_docs(self, client: TestClient) -> None:
        response = client.get("/")
        assert response.status_code == 200
        assert response.json()["service"] == "sentinel-api"


class TestCreateMonitor:
    def test_creates_with_defaults(self, client: TestClient) -> None:
        response = client.post("/api/monitors", json=VALID_MONITOR)
        assert response.status_code == 201

        body = response.json()
        assert body["name"] == "example"
        assert body["method"] == "GET"
        assert body["expected_status"] == 200
        assert body["slo_target"] == 0.995
        assert body["is_active"] is True

    def test_lowercase_method_is_normalised(self, client: TestClient) -> None:
        response = client.post(
            "/api/monitors", json={**VALID_MONITOR, "method": "head"}
        )
        assert response.status_code == 201
        assert response.json()["method"] == "HEAD"

    def test_rejects_non_http_url(self, client: TestClient) -> None:
        response = client.post(
            "/api/monitors", json={**VALID_MONITOR, "url": "ftp://example.com"}
        )
        assert response.status_code == 422

    def test_rejects_unsupported_method(self, client: TestClient) -> None:
        response = client.post(
            "/api/monitors", json={**VALID_MONITOR, "method": "TRACE"}
        )
        assert response.status_code == 422

    def test_rejects_interval_below_minimum(self, client: TestClient) -> None:
        response = client.post(
            "/api/monitors", json={**VALID_MONITOR, "interval_seconds": 5}
        )
        assert response.status_code == 422

    def test_rejects_slo_target_above_one(self, client: TestClient) -> None:
        response = client.post(
            "/api/monitors", json={**VALID_MONITOR, "slo_target": 1.5}
        )
        assert response.status_code == 422


class TestReadMonitors:
    def test_list_is_empty_initially(self, client: TestClient) -> None:
        assert client.get("/api/monitors").json() == []

    def test_list_returns_created_monitors(self, client: TestClient) -> None:
        client.post("/api/monitors", json=VALID_MONITOR)
        client.post("/api/monitors", json={**VALID_MONITOR, "name": "second"})

        body = client.get("/api/monitors").json()
        assert len(body) == 2

    def test_active_only_filter(self, client: TestClient) -> None:
        created = client.post("/api/monitors", json=VALID_MONITOR).json()
        client.patch(f"/api/monitors/{created['id']}", json={"is_active": False})

        assert client.get("/api/monitors", params={"active_only": True}).json() == []
        assert len(client.get("/api/monitors").json()) == 1

    def test_get_missing_monitor_is_404(self, client: TestClient) -> None:
        assert client.get("/api/monitors/999").status_code == 404


class TestUpdateAndDelete:
    def test_partial_update_leaves_other_fields(self, client: TestClient) -> None:
        created = client.post("/api/monitors", json=VALID_MONITOR).json()

        updated = client.patch(
            f"/api/monitors/{created['id']}", json={"name": "renamed"}
        ).json()

        assert updated["name"] == "renamed"
        assert updated["url"] == created["url"]
        assert updated["interval_seconds"] == created["interval_seconds"]

    def test_delete_then_get_is_404(self, client: TestClient) -> None:
        created = client.post("/api/monitors", json=VALID_MONITOR).json()

        assert client.delete(f"/api/monitors/{created['id']}").status_code == 204
        assert client.get(f"/api/monitors/{created['id']}").status_code == 404


class TestSloEndpoint:
    def _seed(
        self, session: Session, up_count: int, down_count: int, slo_target: float = 0.99
    ) -> int:
        monitor = Monitor(
            name="seeded",
            url="https://example.com",
            method="GET",
            interval_seconds=60,
            expected_status=200,
            slo_target=slo_target,
            next_run_at=utcnow(),
        )
        session.add(monitor)
        session.flush()

        now = utcnow()
        for index in range(up_count):
            session.add(
                CheckResult(
                    monitor_id=monitor.id,
                    checked_at=now - timedelta(minutes=index),
                    status_code=200,
                    response_time_ms=100.0,
                    is_up=True,
                )
            )
        for index in range(down_count):
            session.add(
                CheckResult(
                    monitor_id=monitor.id,
                    checked_at=now - timedelta(minutes=index),
                    status_code=500,
                    response_time_ms=None,
                    is_up=False,
                    error="boom",
                )
            )
        session.commit()
        return monitor.id

    def test_reports_no_data_gracefully(self, client: TestClient) -> None:
        created = client.post("/api/monitors", json=VALID_MONITOR).json()

        body = client.get(f"/api/monitors/{created['id']}/slo").json()
        assert body["total_checks"] == 0
        assert body["availability"] is None

    def test_computes_availability_and_budget(
        self, client: TestClient, db_session: Session
    ) -> None:
        monitor_id = self._seed(db_session, up_count=99, down_count=1)

        body = client.get(f"/api/monitors/{monitor_id}/slo").json()
        assert body["total_checks"] == 100
        assert body["successful_checks"] == 99
        assert body["availability"] == 0.99
        assert body["is_meeting_slo"] is True
        assert body["burn_rate"] == 1.0

    def test_excludes_failed_probes_from_latency(
        self, client: TestClient, db_session: Session
    ) -> None:
        monitor_id = self._seed(db_session, up_count=5, down_count=5)

        body = client.get(f"/api/monitors/{monitor_id}/slo").json()
        # Only the 5 successful probes had a latency, all 100ms.
        assert body["p50_ms"] == 100.0

    def test_window_outside_data_returns_nothing(
        self, client: TestClient, db_session: Session
    ) -> None:
        monitor_id = self._seed(db_session, up_count=3, down_count=0)

        # All seeded data is within the last hour; a 1-hour window includes it.
        body = client.get(
            f"/api/monitors/{monitor_id}/slo", params={"window_hours": 1}
        ).json()
        assert body["total_checks"] == 3

    def test_rejects_invalid_window(self, client: TestClient) -> None:
        created = client.post("/api/monitors", json=VALID_MONITOR).json()

        response = client.get(
            f"/api/monitors/{created['id']}/slo", params={"window_hours": 0}
        )
        assert response.status_code == 422


class TestResultsEndpoint:
    def test_returns_empty_for_new_monitor(self, client: TestClient) -> None:
        created = client.post("/api/monitors", json=VALID_MONITOR).json()
        assert client.get(f"/api/monitors/{created['id']}/results").json() == []

    def test_404_for_unknown_monitor(self, client: TestClient) -> None:
        assert client.get("/api/monitors/424242/results").status_code == 404
