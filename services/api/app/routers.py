"""Monitor CRUD plus the SLO reporting endpoint."""

from __future__ import annotations

from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from sentinel_core.db import get_db
from sentinel_core.models import CheckResult, Monitor, utcnow
from sentinel_core.stats import build_report

from .schemas import (
    CheckResultRead,
    MonitorCreate,
    MonitorRead,
    MonitorUpdate,
    SloReportRead,
)

router = APIRouter(prefix="/api/monitors", tags=["monitors"])

# Annotated dependencies are the current FastAPI idiom. Putting Depends() in a
# default argument works but is a mutable-default style trap, so linters flag it.
DbSession = Annotated[Session, Depends(get_db)]


def _get_or_404(session: Session, monitor_id: int) -> Monitor:
    monitor = session.get(Monitor, monitor_id)
    if monitor is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"monitor {monitor_id} not found",
        )
    return monitor


@router.post("", response_model=MonitorRead, status_code=status.HTTP_201_CREATED)
def create_monitor(payload: MonitorCreate, session: DbSession) -> Monitor:
    """Register a new endpoint to watch.

    ``next_run_at`` is set to now so the scheduler picks it up on its next tick
    instead of waiting a full interval for the first sample.
    """
    monitor = Monitor(
        name=payload.name,
        url=payload.url,
        method=payload.method,
        interval_seconds=payload.interval_seconds,
        expected_status=payload.expected_status,
        slo_target=payload.slo_target,
        next_run_at=utcnow(),
    )
    session.add(monitor)
    session.commit()
    session.refresh(monitor)
    return monitor


@router.get("", response_model=list[MonitorRead])
def list_monitors(
    session: DbSession,
    active_only: bool = Query(default=False),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[Monitor]:
    stmt = select(Monitor).order_by(Monitor.id)
    if active_only:
        stmt = stmt.where(Monitor.is_active.is_(True))
    return list(session.scalars(stmt.limit(limit).offset(offset)))


@router.get("/{monitor_id}", response_model=MonitorRead)
def get_monitor(monitor_id: int, session: DbSession) -> Monitor:
    return _get_or_404(session, monitor_id)


@router.patch("/{monitor_id}", response_model=MonitorRead)
def update_monitor(
    monitor_id: int,
    payload: MonitorUpdate,
    session: DbSession,
) -> Monitor:
    monitor = _get_or_404(session, monitor_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(monitor, field, value)
    session.commit()
    session.refresh(monitor)
    return monitor


@router.delete("/{monitor_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_monitor(monitor_id: int, session: DbSession) -> None:
    monitor = _get_or_404(session, monitor_id)
    session.delete(monitor)
    session.commit()


@router.get("/{monitor_id}/results", response_model=list[CheckResultRead])
def list_results(
    monitor_id: int,
    session: DbSession,
    limit: int = Query(default=50, ge=1, le=1000),
) -> list[CheckResult]:
    """Most recent probe samples, newest first."""
    _get_or_404(session, monitor_id)
    stmt = (
        select(CheckResult)
        .where(CheckResult.monitor_id == monitor_id)
        .order_by(CheckResult.checked_at.desc())
        .limit(limit)
    )
    return list(session.scalars(stmt))


@router.get("/{monitor_id}/slo", response_model=SloReportRead)
def get_slo_report(
    monitor_id: int,
    session: DbSession,
    window_hours: int = Query(default=24, ge=1, le=720),
) -> SloReportRead:
    """Availability, error budget and latency percentiles over a time window."""
    monitor = _get_or_404(session, monitor_id)
    since = utcnow() - timedelta(hours=window_hours)

    stmt = select(CheckResult.is_up, CheckResult.response_time_ms).where(
        CheckResult.monitor_id == monitor_id,
        CheckResult.checked_at >= since,
    )
    rows = session.execute(stmt).all()

    total = len(rows)
    successful = sum(1 for is_up, _ in rows if is_up)
    # Failed probes have no meaningful latency, so exclude them from percentiles
    # to avoid reporting timeout durations as if they were real response times.
    latencies = [ms for is_up, ms in rows if is_up and ms is not None]

    report = build_report(
        window_hours=window_hours,
        slo_target=monitor.slo_target,
        latencies_ms=latencies,
        total_checks=total,
        successful_checks=successful,
    )
    # model_validate(obj, from_attributes=True) reads dataclass attributes
    # directly and is typed as accepting Any, unlike **report.to_dict() which
    # unpacks a dict[str, object] that mypy cannot match against SloReportRead's
    # concrete field types.
    return SloReportRead.model_validate(report, from_attributes=True)
