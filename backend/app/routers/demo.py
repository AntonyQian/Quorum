"""Demo panel endpoints (SPEC §8). Clock and simulate-joins; simulate-demand and reset are TODO."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlmodel import Session

from app.db import get_session
from app.deps import get_pool_or_404
from app.models import Pool
from app.schemas import PoolDetail
from app.services import clock, membership, pool_engine, views

router = APIRouter(prefix="/demo")


class AdvanceBody(BaseModel):
    hours: float | None = None
    days: float | None = None
    to_deadline_of_pool: int | None = None


class SimulateJoinsBody(BaseModel):
    count: int = Field(ge=0, le=200)
    include_declining_card: bool = False


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


@router.post("/pools/{pool_id}/simulate-joins", response_model=PoolDetail)
def simulate_joins(body: SimulateJoinsBody, pool: Pool = Depends(get_pool_or_404),
                   session: Session = Depends(get_session)):
    pool = membership.simulate_joins(session, pool, body.count, body.include_declining_card)
    return views.pool_detail(session, pool, None)
