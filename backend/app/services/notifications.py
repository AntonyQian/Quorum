from sqlmodel import Session, select

from app.models import Notification, User
from app.services import clock


def notify(session: Session, user_id: int, kind: str, title: str, body: str = "", link: str | None = None) -> None:
    session.add(
        Notification(user_id=user_id, kind=kind, title=title, body=body, link=link, created_at=clock.now(session))
    )


def notify_retailer(session: Session, retailer_id: int, kind: str, title: str, body: str = "", link: str | None = None) -> None:
    users = session.exec(select(User).where(User.retailer_id == retailer_id, User.role == "retailer")).all()
    for user in users:
        notify(session, user.id, kind, title, body, link)
