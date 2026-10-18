"""Accounts and shopper endpoints (SPEC §8)."""

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.db import get_session
from app.deps import current_user, get_public_pool_or_404, optional_user
from app.errors import api_error, not_found
from app.models import Notification, Pool, PoolMember, Product, User
from app.schemas import (
    NotificationList,
    Order,
    PoolDetail,
    PoolSummary,
    RecommendBody,
    RecommendResponse,
    UserOut,
)
from app.services import membership, notifications, pool_engine, recommender, views

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
    query = (
        select(Pool)
        .join(Product, Product.id == Pool.product_id)
        .where(Pool.status.in_(statuses), Product.visibility == "public")
    )
    if category:
        query = query.where(Product.category == category)
    return [views.pool_summary(session, p) for p in session.exec(query.order_by(Pool.deadline)).all()]


@router.get("/pools/{pool_id}", response_model=PoolDetail)
def get_pool(viewer: User | None = Depends(optional_user), pool: Pool = Depends(get_public_pool_or_404),
             session: Session = Depends(get_session)):
    pool = pool_engine.evaluate_pool(session, pool)
    return views.pool_detail(session, pool, viewer)


@router.post("/pools/{pool_id}/join", response_model=PoolDetail)
def join_pool(user: User = Depends(current_user), pool: Pool = Depends(get_public_pool_or_404),
              session: Session = Depends(get_session)):
    return views.pool_detail(session, membership.join(session, pool, user), user)


@router.post("/pools/{pool_id}/leave", response_model=PoolDetail)
def leave_pool(user: User = Depends(current_user), pool: Pool = Depends(get_public_pool_or_404),
               session: Session = Depends(get_session)):
    return views.pool_detail(session, membership.leave(session, pool, user), user)


@router.post("/recommend", response_model=RecommendResponse)
def recommend(body: RecommendBody, user: User = Depends(current_user), session: Session = Depends(get_session)):
    if not body.text.strip():
        raise api_error(422, "invalid_request", "Describe what you're looking for")
    try:
        return recommender.recommend(session, user, body.text)
    except recommender.RecommenderError as e:
        raise api_error(502, "recommender_unavailable", f"Recommendations are unavailable right now: {e}")


@router.get("/me/orders", response_model=list[Order])
def my_orders(user: User = Depends(current_user), session: Session = Depends(get_session)):
    members = session.exec(select(PoolMember).where(PoolMember.user_id == user.id).order_by(PoolMember.id.desc())).all()
    return [views.order(session, m) for m in members]


@router.get("/me/notifications", response_model=NotificationList)
def my_notifications(user: User = Depends(current_user), session: Session = Depends(get_session)):
    return notifications.list_for(session, user.id)


@router.post("/notifications/{notification_id}/read")
def mark_read(notification_id: int, user: User = Depends(current_user), session: Session = Depends(get_session)):
    n = session.get(Notification, notification_id)
    if n is None or n.user_id != user.id:
        raise not_found("Notification")
    n.read = True
    session.add(n)
    session.commit()
    return {"ok": True}
