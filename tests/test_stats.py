"""Tests for the SLO maths.

These are the highest-value tests in the project: an uptime tool that computes
availability incorrectly is worse than no tool at all.
"""

from __future__ import annotations

import pytest

from sentinel_core.stats import build_report, percentile


class TestPercentile:
    def test_empty_returns_none(self) -> None:
        assert percentile([], 0.5) is None

    def test_single_value(self) -> None:
        assert percentile([42.0], 0.99) == 42.0

    def test_median_of_odd_length(self) -> None:
        assert percentile([1.0, 2.0, 3.0], 0.5) == 2.0

    def test_median_interpolates_on_even_length(self) -> None:
        assert percentile([1.0, 2.0, 3.0, 4.0], 0.5) == 2.5

    def test_p95_of_hundred_values(self) -> None:
        values = [float(n) for n in range(1, 101)]
        # rank = 0.95 * 99 = 94.05 -> between values[94]=95 and values[95]=96
        assert percentile(values, 0.95) == pytest.approx(95.05)

    def test_p100_is_max(self) -> None:
        assert percentile([1.0, 5.0, 9.0], 1.0) == 9.0


class TestBuildReport:
    def test_no_data_yields_none_availability(self) -> None:
        report = build_report(
            window_hours=24,
            slo_target=0.99,
            latencies_ms=[],
            total_checks=0,
            successful_checks=0,
        )
        assert report.availability is None
        assert report.is_meeting_slo is None
        assert report.total_checks == 0

    def test_perfect_availability(self) -> None:
        report = build_report(
            window_hours=24,
            slo_target=0.99,
            latencies_ms=[10.0] * 100,
            total_checks=100,
            successful_checks=100,
        )
        assert report.availability == 1.0
        assert report.failed_checks == 0
        assert report.is_meeting_slo is True
        assert report.burn_rate == 0.0
        assert report.error_budget_remaining_pct == 100.0

    def test_budget_exactly_exhausted_still_meets_slo(self) -> None:
        # 99% SLO over 100 checks allows exactly 1 failure.
        report = build_report(
            window_hours=24,
            slo_target=0.99,
            latencies_ms=[10.0] * 99,
            total_checks=100,
            successful_checks=99,
        )
        assert report.availability == 0.99
        assert report.is_meeting_slo is True
        assert report.error_budget_total == pytest.approx(1.0)
        assert report.burn_rate == 1.0
        assert report.error_budget_remaining_pct == 0.0

    def test_budget_overspent_breaches_slo(self) -> None:
        # 3 failures against a budget of 1 is a 3x burn rate.
        report = build_report(
            window_hours=24,
            slo_target=0.99,
            latencies_ms=[10.0] * 97,
            total_checks=100,
            successful_checks=97,
        )
        assert report.is_meeting_slo is False
        assert report.burn_rate == 3.0
        assert report.error_budget_remaining < 0
        assert report.error_budget_remaining_pct == -200.0

    def test_hundred_percent_slo_has_no_budget(self) -> None:
        report = build_report(
            window_hours=1,
            slo_target=1.0,
            latencies_ms=[5.0],
            total_checks=10,
            successful_checks=9,
        )
        # No budget exists, so burn rate is undefined rather than infinite.
        assert report.error_budget_total == 0.0
        assert report.burn_rate is None
        assert report.error_budget_remaining_pct is None
        assert report.is_meeting_slo is False

    def test_percentiles_are_populated(self) -> None:
        report = build_report(
            window_hours=24,
            slo_target=0.995,
            latencies_ms=[float(n) for n in range(1, 101)],
            total_checks=100,
            successful_checks=100,
        )
        assert report.p50_ms == pytest.approx(50.5)
        assert report.p95_ms == pytest.approx(95.05)
        assert report.p99_ms == pytest.approx(99.01)

    def test_successful_greater_than_total_does_not_go_negative(self) -> None:
        # Defensive: bad inputs must not produce negative failure counts.
        report = build_report(
            window_hours=1,
            slo_target=0.99,
            latencies_ms=[],
            total_checks=5,
            successful_checks=10,
        )
        assert report.failed_checks == 0
