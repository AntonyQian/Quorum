from fastapi import Depends, Header
from sqlmodel import Session

from app.db import get_session
from app.errors import api_error, forbidden
from app.models import User


def optional_user(
    x_user_id: int | None = Header(default=None),
    session: Session = Depends(get_session),
) -> User | None:
    if x_user_id is None:
        return None
    return session.get(User, x_user_id)


def current_user(user: User | None = Depends(optional_user)) -> User:
    if user is None:
        raise api_error(401, "forbidden", "Missing or unknown X-User-Id header")
    return user


def retailer_user(user: User = Depends(current_user)) -> User:
    if user.role != "retailer":
        raise forbidden("Retailer account required")
    return user
