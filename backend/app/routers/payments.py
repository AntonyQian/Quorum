"""Payment endpoints (SPEC §8): save a card through the payments adapter (mock or Stripe)."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlmodel import Session

from app.db import get_session
from app.deps import current_user
from app.models import User
from app.services import payments

router = APIRouter(prefix="/payments")


class SetupSessionBody(BaseModel):
    return_to: str | None = None


class ConfirmSetupBody(BaseModel):
    session_id: str


@router.post("/setup-session")
def setup_session(body: SetupSessionBody | None = None, user: User = Depends(current_user)):
    return {"url": payments.create_setup_session(user, body.return_to if body else None)}


@router.post("/confirm-setup")
def confirm_setup(body: ConfirmSetupBody, user: User = Depends(current_user),
                  session: Session = Depends(get_session)):
    return {"card_label": payments.confirm_setup(session, user, body.session_id)}
