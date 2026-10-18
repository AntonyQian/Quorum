"""Shared fixtures and helpers: an in-memory SQLite engine, a session on it, a TestClient wired to that
session, and helpers for acting as a user and checking SPEC §3 errors."""

from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app import models  # noqa: F401  (register tables)
from app.db import get_session
from app.main import app
from app.services import clock

T0 = datetime(2026, 10, 17, 12, 0, 0)


def make_engine():
    """A fresh, empty in-memory SQLite engine shared across threads (no tables created)."""
    return create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)


@pytest.fixture(autouse=True)
def enable_demo_panel(monkeypatch):
    monkeypatch.setattr("app.config.DEMO_PANEL_ENABLED", True)


@pytest.fixture
def engine():
    engine = make_engine()
    SQLModel.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def session(engine):
    with Session(engine) as s:
        clock.set_now(s, T0)
        yield s


@pytest.fixture
def client(engine):
    def override_get_session():
        with Session(engine) as s:
            yield s

    app.dependency_overrides[get_session] = override_get_session
    # No `with`: skip the lifespan so tests never touch the on-disk database.
    yield TestClient(app)
    app.dependency_overrides.clear()


def as_user(user):
    return {"X-User-Id": str(user.id)}


def assert_error(response, status, code):
    assert response.status_code == status, response.text
    body = response.json()
    assert set(body) == {"detail"}
    assert set(body["detail"]) == {"code", "message"}
    assert body["detail"]["code"] == code
    assert isinstance(body["detail"]["message"], str) and body["detail"]["message"]
