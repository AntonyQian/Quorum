"""Demo panel endpoints (SPEC §8). Clock only for now; simulate-joins, simulate-demand and reset are TODO."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlmodel import Session

from app.db import get_session
from app.models import Pool
from app.services import clock, pool_engine

router = APIRouter(prefix="/demo")


class AdvanceBody(BaseModel):
    hours: float | None = None
    days: float | None = None
    to_deadline_of_pool: int | None = None


@router.get("/clock")
def get_clock(session: Session = Depends(get_session)):
    return {"now": clock.iso(clock.now(session))}


@router.post("/clock/advance")
def advance_clock(body: AdvanceBody, session: Session = Depends(get_session)):
    if body.to_deadline_of_pool is not None:
        pool = session.get(Pool, body.to_deadline_of_pool)
        if pool is not None:
            clock.set_now(session, max(clock.now(session), pool.deadline))
    clock.advance(session, hours=body.hours or 0, days=body.days or 0)
    pool_engine.evaluate_all(session)
    return {"now": clock.iso(clock.now(session))}
