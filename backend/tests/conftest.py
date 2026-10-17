"""Shared fixtures: an in-memory SQLite engine, a session on it, and a TestClient wired to that session."""

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


@pytest.fixture
def engine():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
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
