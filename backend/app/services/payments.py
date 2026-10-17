"""Payments adapter (SPEC §5). Mock or Stripe, chosen by MOCK_PAYMENTS.

Every charge and refund is written to the `payments` table. Stripe mode is not wired yet.
"""

from sqlmodel import Session

from app import config
from app.models import Payment, PoolMember, User
from app.services import clock


def create_setup_session(user: User, return_to: str | None = None) -> str:
    if config.MOCK_PAYMENTS:
        return f"{config.FRONTEND_URL}/payment/success?session_id=mock_{user.id}"
    raise NotImplementedError("Stripe setup session not implemented yet")


def confirm_setup(session: Session, user: User, session_id: str) -> str:
    if config.MOCK_PAYMENTS:
        user.card_label = "Visa •••• 4242"
        user.card_declines = False  # a newly saved card replaces the declining one
        session.add(user)
        session.commit()
        return user.card_label
    raise NotImplementedError("Stripe confirm-setup not implemented yet")


def charge(session: Session, member: PoolMember, user: User, amount_cents: int) -> bool:
    """Charge the member's card and record it. Adds to member.charged_cents on success."""
    if config.MOCK_PAYMENTS:
        ok = not user.card_declines
        ref = f"mock_ch_{member.id}_{amount_cents}" if ok else ""
    else:
        raise NotImplementedError("Stripe charge not implemented yet")
    session.add(
        Payment(
            pool_member_id=member.id,
            kind="charge",
            amount_cents=amount_cents,
            status="succeeded" if ok else "failed",
            provider_ref=ref,
            created_at=clock.now(session),
        )
    )
    if ok:
        member.charged_cents += amount_cents
        session.add(member)
    return ok


def refund(session: Session, member: PoolMember, amount_cents: int) -> str:
    """Refund part of the member's charge and record it. Adds to member.refunded_cents."""
    if config.MOCK_PAYMENTS:
        ref = f"mock_re_{member.id}_{amount_cents}"
    else:
        raise NotImplementedError("Stripe refund not implemented yet")
    session.add(
        Payment(
            pool_member_id=member.id,
            kind="refund",
            amount_cents=amount_cents,
            status="succeeded",
            provider_ref=ref,
            created_at=clock.now(session),
        )
    )
    member.refunded_cents += amount_cents
    session.add(member)
    return ref
