"""Shared test fixtures.

Unit tests run against in-memory SQLite so CI needs no services and the suite
finishes in seconds. The scheduler's ``SKIP LOCKED`` behaviour is Postgres-only
and is therefore covered by integration tests instead (marked ``integration``).
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from sentinel_core.db import get_db
from sentinel_core.models import Base


@pytest.fixture
def db_session() -> Iterator[Session]:
    """Fresh in-memory database per test.

    StaticPool keeps a single connection alive so the schema created here is
    visible to the code under test; the default pool would hand out a new,
    empty database on each connection.
    """
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = factory()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture
def client(db_session: Session) -> Iterator[TestClient]:
    """API client with the database dependency overridden."""
    from app.main import app

    def override_get_db() -> Iterator[Session]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
