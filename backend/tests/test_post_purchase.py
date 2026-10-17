"""My Orders and notifications endpoints, driven by a real Lock + Settlement."""

from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlmodel import select

from app.db import get_session
from app.main import app
from app.models import User
from app.services import pool_engine
from tests.test_pool_engine import T0, join, make_pool, session  # noqa: F401


@pytest.fixture
def client(session):
    app.dependency_overrides[get_session] = lambda: session
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_orders_and_notifications_after_settlement(client, session):
    pool = make_pool(session)
    members = [join(session, pool, n) for n in "abc"]
    declined = join(session, pool, "d", declines=True)
    pool_engine.evaluate_pool(session, pool)
    pool_engine.evaluate_pool(session, pool, T0 + timedelta(days=15))
    a = {"X-User-Id": str(members[0].user_id)}

    orders = client.get("/api/me/orders", headers=a).json()
    assert len(orders) == 1
    o = orders[0]
    assert (o["pool_status"], o["member_status"]) == ("completed", "charged")
    assert [p["kind"] for p in o["payments"]] == ["charge"]
    assert o["net_paid_cents"] == o["charged_cents"] - o["refunded_cents"] == 90_000

    bad = client.get("/api/me/orders", headers={"X-User-Id": str(declined.user_id)}).json()[0]
    assert bad["member_status"] == "payment_failed"
    assert bad["payments"][0]["status"] == "failed"

    n = client.get("/api/me/notifications", headers=a).json()
    assert n["unread"] == len(n["items"]) >= 2
    first = n["items"][0]
    assert client.post(f"/api/notifications/{first['id']}/read", headers=a).json() == {"ok": True}
    assert client.get("/api/me/notifications", headers=a).json()["unread"] == n["unread"] - 1

    owner = session.exec(select(User).where(User.role == "retailer")).first()
    r = client.get("/api/retailer/notifications", headers={"X-User-Id": str(owner.id)}).json()
    assert {i["kind"] for i in r["items"]} == {"pool_locked", "pool_completed"}
