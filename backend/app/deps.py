from fastapi import Depends, Header
from sqlmodel import Session

from app.db import get_session
from app.errors import api_error, forbidden, not_found
from app.models import Pool, User


def optional_user(
    x_user_id: str | None = Header(default=None),
    session: Session = Depends(get_session),
) -> User | None:
    """The account named by X-User-Id, or None when the header is missing, malformed, or unknown."""
    if x_user_id is None or not x_user_id.strip().isdigit():
        return None
    return session.get(User, int(x_user_id))


def current_user(user: User | None = Depends(optional_user)) -> User:
    if user is None:
        raise api_error(401, "forbidden", "Missing or unknown X-User-Id header")
    return user


def retailer_user(user: User = Depends(current_user)) -> User:
    if user.role != "retailer":
        raise forbidden("Retailer account required")
    return user


def get_pool_or_404(pool_id: int, session: Session = Depends(get_session)) -> Pool:
    """The Pool named by the `pool_id` path parameter, or 404 `not_found`."""
    pool = session.get(Pool, pool_id)
    if pool is None:
        raise not_found("Pool")
    return pool
