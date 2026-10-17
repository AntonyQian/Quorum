"""Retailer endpoints (SPEC §8): product CRUD, launch, demand, pool view. TODO."""

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.db import get_session
from app.deps import retailer_user
from app.models import User
from app.schemas import NotificationList
from app.services import notifications

router = APIRouter(prefix="/retailer", dependencies=[Depends(retailer_user)])


@router.get("/notifications", response_model=NotificationList)
def retailer_notifications(user: User = Depends(retailer_user), session: Session = Depends(get_session)):
    return notifications.list_for(session, user.id)
