"""Ticket #7 acceptance: server boots, §7 tables, re-runnable seed, Sim Clock, CORS, env defaults."""

import importlib
import re
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy import inspect
from sqlmodel import Session, func, select

from app import config
from app.models import Pool, Product, Retailer, User
from app.services import clock
from seed import seed as seed_module

from tests.conftest import make_engine

SPEC_TABLES = {
    "retailers", "users", "products", "pools", "tiers", "pool_members",
    "payments", "wishes", "demand_hits", "notifications", "sim_clock",
}
BACKEND = Path(__file__).resolve().parents[1]


def fresh_engine():
    return make_engine()


def counts(engine) -> dict[str, int]:
    with Session(engine) as s:
        return {m.__name__: s.exec(select(func.count()).select_from(m)).one() for m in (Retailer, User, Product, Pool)}


def test_api_docs_page_loads(client):
    assert client.get("/docs").status_code == 200
    assert client.get("/openapi.json").status_code == 200


def test_init_creates_every_spec_table():
    engine = fresh_engine()
    seed_module.reset_and_seed(engine)
    assert SPEC_TABLES <= set(inspect(engine).get_table_names())


def test_seed_loads_starter_data_and_can_be_rerun():
    engine = fresh_engine()
    seed_module.reset_and_seed(engine)
    first = counts(engine)
    seed_module.reset_and_seed(engine)
    assert counts(engine) == first
    assert first["Retailer"] >= 2 and first["Product"] >= 3 and first["Pool"] >= 2
    with Session(engine) as s:
        names = {u.name for u in s.exec(select(User)).all()}
        assert {"Alice", "Bob"} <= names
        assert s.exec(select(User).where(User.role == "retailer")).first() is not None
        assert clock.now(s) == clock.DEFAULT_START


def test_sim_clock_reads_and_advances(session):
    start = clock.now(session)
    assert clock.advance(session, days=2, hours=3) == start + timedelta(days=2, hours=3)
    assert clock.now(session) == start + timedelta(days=2, hours=3)
    assert clock.set_now(session, datetime(2026, 11, 1)) == datetime(2026, 11, 1)
    assert clock.now(session) == datetime(2026, 11, 1)


def test_nothing_outside_the_sim_clock_reads_real_time():
    pattern = re.compile(r"\b(datetime\.now|datetime\.utcnow|utcnow|date\.today|time\.time)\s*\(")
    offenders = [
        str(path.relative_to(BACKEND))
        for folder in ("app", "seed")
        for path in (BACKEND / folder).rglob("*.py")
        if path.name != "clock.py" and pattern.search(path.read_text(encoding="utf-8"))
    ]
    assert offenders == []


def test_cors_allows_the_frontend_origin(client):
    response = client.options(
        "/health",
        headers={"Origin": config.FRONTEND_URL, "Access-Control-Request-Method": "GET"},
    )
    assert response.headers.get("access-control-allow-origin") == config.FRONTEND_URL


def test_env_defaults_mock_payments_to_true(monkeypatch):
    for var in ("MOCK_PAYMENTS", "FRONTEND_URL", "CLAUDE_MODEL", "STRIPE_SECRET_KEY", "ANTHROPIC_API_KEY"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setattr("dotenv.load_dotenv", lambda *a, **k: False)
    try:
        fresh = importlib.reload(config)
        assert fresh.MOCK_PAYMENTS is True
        assert fresh.FRONTEND_URL == "http://localhost:3000"
        assert fresh.CLAUDE_MODEL
    finally:
        monkeypatch.undo()
        importlib.reload(config)


def test_env_vars_are_read(monkeypatch):
    monkeypatch.setenv("MOCK_PAYMENTS", "false")
    monkeypatch.setenv("FRONTEND_URL", "http://example.test:4000")
    try:
        fresh = importlib.reload(config)
        assert fresh.MOCK_PAYMENTS is False
        assert fresh.FRONTEND_URL == "http://example.test:4000"
    finally:
        monkeypatch.undo()
        importlib.reload(config)
