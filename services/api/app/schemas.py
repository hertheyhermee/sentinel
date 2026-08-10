"""Request and response models.

Validation lives here so invalid input is rejected at the edge with a 422 and a
useful message, rather than becoming a confusing database error deeper in.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

ALLOWED_METHODS = {"GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"}


class MonitorCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    url: str = Field(min_length=1, max_length=2048)
    method: str = Field(default="GET")
    interval_seconds: int = Field(default=60, ge=10, le=86_400)
    expected_status: int = Field(default=200, ge=100, le=599)
    slo_target: float = Field(default=0.995, gt=0.0, le=1.0)

    @field_validator("url")
    @classmethod
    def url_must_be_http(cls, value: str) -> str:
        if not value.startswith(("http://", "https://")):
            raise ValueError("url must start with http:// or https://")
        return value

    @field_validator("method")
    @classmethod
    def method_must_be_supported(cls, value: str) -> str:
        upper = value.upper()
        if upper not in ALLOWED_METHODS:
            allowed = ", ".join(sorted(ALLOWED_METHODS))
            raise ValueError(f"method must be one of: {allowed}")
        return upper


class MonitorUpdate(BaseModel):
    """All fields optional; only what is supplied gets changed."""

    name: str | None = Field(default=None, min_length=1, max_length=128)
    interval_seconds: int | None = Field(default=None, ge=10, le=86_400)
    expected_status: int | None = Field(default=None, ge=100, le=599)
    slo_target: float | None = Field(default=None, gt=0.0, le=1.0)
    is_active: bool | None = None


class MonitorRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    url: str
    method: str
    interval_seconds: int
    expected_status: int
    slo_target: float
    is_active: bool
    next_run_at: datetime
    created_at: datetime


class CheckResultRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    monitor_id: int
    checked_at: datetime
    status_code: int | None
    response_time_ms: float | None
    is_up: bool
    error: str | None


class SloReportRead(BaseModel):
    """Mirrors sentinel_core.stats.SloReport."""

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


class HealthRead(BaseModel):
    status: str
    checks: dict[str, str]
