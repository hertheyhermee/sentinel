"""SLI, SLO and error-budget computation.

Definitions used here, matching standard SRE practice:

* **SLI** — the measured ratio ``good events / valid events``. Here: successful
  probes divided by total probes in the window.
* **SLO** — the target for that ratio, e.g. 0.995.
* **Error budget** — the failures you are allowed to spend and still meet the
  SLO: ``(1 - slo_target) * total``.
* **Burn rate** — how fast you are consuming that budget relative to the pace
  that would exactly exhaust it over the window. A burn rate of 1.0 means you
  will finish the window exactly on target; 14.4 is the classic fast-burn
  page threshold from the Google SRE workbook.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class SloReport:
    """Everything needed to render an SLO panel."""

    window_hours: int
    total_checks: int
    successful_checks: int
    failed_checks: int

    availability: float | None
    slo_target: float

    error_budget_total: float
    error_budget_consumed: float
    error_budget_remaining: float
    error_budget_remaining_pct: float | None
    burn_rate: float | None
    is_meeting_slo: bool | None

    p50_ms: float | None
    p95_ms: float | None
    p99_ms: float | None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def percentile(sorted_values: list[float], fraction: float) -> float | None:
    """Linear-interpolation percentile over a pre-sorted list.

    Implemented directly so the same numbers can be produced in tests without a
    database. Postgres ``percentile_cont`` is used on the hot path instead.
    """
    if not sorted_values:
        return None
    if len(sorted_values) == 1:
        return round(sorted_values[0], 2)

    rank = fraction * (len(sorted_values) - 1)
    low = int(rank)
    high = min(low + 1, len(sorted_values) - 1)
    weight = rank - low
    value = sorted_values[low] * (1 - weight) + sorted_values[high] * weight
    return round(value, 2)


def build_report(
    window_hours: int,
    slo_target: float,
    latencies_ms: list[float],
    total_checks: int,
    successful_checks: int,
) -> SloReport:
    """Derive availability, error budget and latency percentiles."""
    failed_checks = max(total_checks - successful_checks, 0)

    availability = successful_checks / total_checks if total_checks else None

    # The budget is expressed in "number of failed checks we can afford".
    error_budget_total = (1.0 - slo_target) * total_checks
    error_budget_consumed = float(failed_checks)
    error_budget_remaining = error_budget_total - error_budget_consumed

    if error_budget_total > 0:
        remaining_pct = round((error_budget_remaining / error_budget_total) * 100.0, 2)
        burn_rate = round(error_budget_consumed / error_budget_total, 3)
    else:
        # A 100% SLO leaves no budget, so any failure is an immediate breach.
        remaining_pct = None
        burn_rate = None

    ordered = sorted(latencies_ms)

    return SloReport(
        window_hours=window_hours,
        total_checks=total_checks,
        successful_checks=successful_checks,
        failed_checks=failed_checks,
        availability=round(availability, 5) if availability is not None else None,
        slo_target=slo_target,
        error_budget_total=round(error_budget_total, 3),
        error_budget_consumed=round(error_budget_consumed, 3),
        error_budget_remaining=round(error_budget_remaining, 3),
        error_budget_remaining_pct=remaining_pct,
        burn_rate=burn_rate,
        is_meeting_slo=(availability >= slo_target)
        if availability is not None
        else None,
        p50_ms=percentile(ordered, 0.50),
        p95_ms=percentile(ordered, 0.95),
        p99_ms=percentile(ordered, 0.99),
    )
