"""Sim Clock: the single source of "now" (ADR 0003). Never call datetime.now() in business logic."""

from datetime import datetime, timedelta

from sqlmodel import Session

from app.models import SimClock

DEFAULT_START = datetime(2026, 10, 17, 12, 0, 0)


def now(session: Session) -> datetime:
    row = session.get(SimClock, 1)
    if row is None:
        row = SimClock(id=1, now=DEFAULT_START)
        session.add(row)
        session.commit()
    return row.now


def set_now(session: Session, value: datetime) -> datetime:
    row = session.get(SimClock, 1)
    if row is None:
        row = SimClock(id=1, now=value)
    row.now = value
    session.add(row)
    session.commit()
    return value


def advance(session: Session, *, hours: float = 0, days: float = 0) -> datetime:
    return set_now(session, now(session) + timedelta(hours=hours, days=days))


def iso(value: datetime) -> str:
    return value.strftime("%Y-%m-%dT%H:%M:%SZ")
