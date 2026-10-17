"""Accounts and shopper endpoints (SPEC §8). Recommend, orders and notifications are still TODO."""

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.db import get_session
from app.deps import current_user, optional_user
from app.errors import not_found
from app.models import Pool, Product, User
from app.schemas import PoolDetail, PoolSummary, UserOut
from app.services import membership, pool_engine, views

router = APIRouter()


@router.get("/users", response_model=list[UserOut])
def list_users(include_simulated: bool = False, session: Session = Depends(get_session)):
    query = select(User)
    if not include_simulated:
        query = query.where(User.is_simulated == False)  # noqa: E712
    return [views.user_out(u) for u in session.exec(query.order_by(User.id)).all()]


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(current_user)):
    return views.user_out(user)


@router.get("/pools", response_model=list[PoolSummary])
def list_pools(status: str = "open,locked", category: str | None = None, session: Session = Depends(get_session)):
    pool_engine.evaluate_all(session)
    statuses = [s.strip() for s in status.split(",") if s.strip()]
    query = select(Pool).where(Pool.status.in_(statuses))
    if category:
        query = query.join(Product, Product.id == Pool.product_id).where(Product.category == category)
    return [views.pool_summary(session, p) for p in session.exec(query.order_by(Pool.deadline)).all()]


@router.get("/pools/{pool_id}", response_model=PoolDetail)
def get_pool(pool_id: int, viewer: User | None = Depends(optional_user), session: Session = Depends(get_session)):
    pool = session.get(Pool, pool_id)
    if pool is None:
        raise not_found("Pool")
    pool = pool_engine.evaluate_pool(session, pool)
    return views.pool_detail(session, pool, viewer)


@router.post("/pools/{pool_id}/join", response_model=PoolDetail)
def join_pool(pool_id: int, user: User = Depends(current_user), session: Session = Depends(get_session)):
    pool = session.get(Pool, pool_id)
    if pool is None:
        raise not_found("Pool")
    return views.pool_detail(session, membership.join(session, pool, user), user)


@router.post("/pools/{pool_id}/leave", response_model=PoolDetail)
def leave_pool(pool_id: int, user: User = Depends(current_user), session: Session = Depends(get_session)):
    pool = session.get(Pool, pool_id)
    if pool is None:
        raise not_found("Pool")
    return views.pool_detail(session, membership.leave(session, pool, user), user)
