"""Database models.

Two tables only:

* ``monitors``      — what to probe and how often.
* ``check_results`` — the append-only outcome of every probe. This is the
  raw SLI data that uptime, latency percentiles and error budgets derive from.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    """Timezone-aware UTC now. Never store naive datetimes."""
    return datetime.now(UTC)


class Base(DeclarativeBase):
    """Declarative base. Alembic autogenerate reads Base.metadata."""


class Monitor(Base):
    __tablename__ = "monitors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    method: Mapped[str] = mapped_column(String(10), nullable=False, default="GET")

    # How frequently to probe, in seconds.
    interval_seconds: Mapped[int] = mapped_column(
        Integer, nullable=False, default=60, server_default="60"
    )

    # A probe counts as "up" only when the response status matches this.
    expected_status: Mapped[int] = mapped_column(
        Integer, nullable=False, default=200, server_default="200"
    )

    # Target availability for the error budget, e.g. 0.995 == 99.5%.
    slo_target: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.995, server_default="0.995"
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )

    # Scheduler claims monitors whose next_run_at has passed.
    next_run_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    results: Mapped[list[CheckResult]] = relationship(
        back_populates="monitor",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (
        # Supports the scheduler's "which monitors are due?" query.
        Index("ix_monitors_due", "is_active", "next_run_at"),
    )


class CheckResult(Base):
    __tablename__ = "check_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    monitor_id: Mapped[int] = mapped_column(
        ForeignKey("monitors.id", ondelete="CASCADE"), nullable=False
    )

    checked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Null when the request never completed (DNS failure, timeout, refused).
    status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    response_time_ms: Mapped[float | None] = mapped_column(Float, nullable=True)

    is_up: Mapped[bool] = mapped_column(Boolean, nullable=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    monitor: Mapped[Monitor] = relationship(back_populates="results")

    __table_args__ = (
        # Supports "recent results for this monitor", the hot read path.
        Index("ix_check_results_monitor_time", "monitor_id", "checked_at"),
    )
