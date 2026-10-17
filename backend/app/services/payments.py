"""Payments adapter (SPEC §5). Mock or Stripe, chosen by MOCK_PAYMENTS.

Every charge and refund is written to the `payments` table. Stripe mode uses test keys and no webhooks:
Checkout in setup mode saves a card on a Customer, Lock charges are off-session PaymentIntents, and Tier
Refunds are partial Refunds on the charge's PaymentIntent.
"""

import stripe
from sqlmodel import Session, select

from app import config
from app.errors import api_error
from app.models import Payment, PoolMember, User
from app.services import clock


SIM_WORKING_CARD = "pm_card_visa"
SIM_DECLINING_CARD = "pm_card_chargeCustomerFail"  # Stripe test card: attaches fine, fails when charged


def _stripe():
    stripe.api_key = config.STRIPE_SECRET_KEY
    return stripe


def _frontend_url(path_or_url: str) -> str:
    if path_or_url.startswith(("http://", "https://")):
        return path_or_url
    return f"{config.FRONTEND_URL}/{path_or_url.lstrip('/')}"


def _ensure_customer(session: Session, user: User) -> str:
    if not user.stripe_customer_id:
        customer = _stripe().Customer.create(name=user.name, metadata={"quorum_user_id": str(user.id)})
        user.stripe_customer_id = customer.id
        session.add(user)
    return user.stripe_customer_id


def create_setup_session(session: Session, user: User, return_to: str | None = None) -> str:
    if config.MOCK_PAYMENTS:
        return f"{config.FRONTEND_URL}/payment/success?session_id=mock_{user.id}"
    customer_id = _ensure_customer(session, user)
    session.commit()
    checkout = _stripe().checkout.Session.create(
        mode="setup",
        customer=customer_id,
        currency="usd",
        payment_method_types=["card"],
        success_url=f"{config.FRONTEND_URL}/payment/success?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=_frontend_url(return_to or "/"),
    )
    return checkout.url


def confirm_setup(session: Session, user: User, session_id: str) -> str:
    if config.MOCK_PAYMENTS:
        user.card_label = "Visa •••• 4242"
        user.card_declines = False  # a newly saved card replaces the declining one
        session.add(user)
        session.commit()
        return user.card_label
    try:
        checkout = _stripe().checkout.Session.retrieve(session_id, expand=["setup_intent.payment_method"])
    except stripe.StripeError:
        raise api_error(400, "invalid_request", "Unknown card-saving session")
    intent = checkout.setup_intent
    if not user.stripe_customer_id or checkout.customer != user.stripe_customer_id:
        raise api_error(400, "invalid_request", "This card-saving session belongs to someone else")
    if intent is None or intent.status != "succeeded":
        raise api_error(400, "invalid_request", "Card saving was not completed")
    card = intent.payment_method.card
    user.stripe_payment_method_id = intent.payment_method.id
    user.card_label = f"{card.brand.title()} •••• {card.last4}"
    user.card_declines = False
    session.add(user)
    session.commit()
    return user.card_label


def _ensure_simulated_card(session: Session, user: User) -> None:
    """Give a Simulated Shopper a Stripe test customer and test card the first time they are charged.
    The declining one gets a card that saves fine but fails when charged."""
    if user.stripe_payment_method_id:
        return
    token = SIM_DECLINING_CARD if user.card_declines else SIM_WORKING_CARD
    customer_id = _ensure_customer(session, user)
    user.stripe_payment_method_id = _stripe().PaymentMethod.attach(token, customer=customer_id).id
    session.add(user)


def _stripe_charge(session: Session, member: PoolMember, user: User, amount_cents: int) -> tuple[bool, str]:
    if user.is_simulated:
        _ensure_simulated_card(session, user)
    if not (user.stripe_customer_id and user.stripe_payment_method_id):
        return False, ""  # no card saved through Stripe (e.g. one saved while in mock mode)
    try:
        intent = _stripe().PaymentIntent.create(
            amount=amount_cents,
            currency="usd",
            customer=user.stripe_customer_id,
            payment_method=user.stripe_payment_method_id,
            off_session=True,
            confirm=True,
            metadata={"quorum_pool_member_id": str(member.id)},
        )
    except stripe.CardError as exc:
        failed = getattr(exc.error, "payment_intent", None)
        return False, getattr(failed, "id", "") or ""
    except stripe.StripeError:
        return False, ""
    return intent.status == "succeeded", intent.id


def charge(session: Session, member: PoolMember, user: User, amount_cents: int) -> bool:
    """Charge the member's card and record it. Adds to member.charged_cents on success."""
    if config.MOCK_PAYMENTS:
        ok = not user.card_declines
        ref = f"mock_ch_{member.id}_{amount_cents}" if ok else ""
    else:
        ok, ref = _stripe_charge(session, member, user, amount_cents)
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


def _refundable_charge_ref(session: Session, member: PoolMember, amount_cents: int) -> str:
    """The PaymentIntent of the member's latest succeeded charge large enough to cover the Tier Refund."""
    charges = session.exec(
        select(Payment)
        .where(Payment.pool_member_id == member.id, Payment.kind == "charge", Payment.status == "succeeded",
               Payment.amount_cents >= amount_cents)
        .order_by(Payment.id.desc())
    ).first()
    if charges is None:
        raise ValueError(f"Pool Member {member.id} has no charge to refund {amount_cents} cents from")
    return charges.provider_ref


def refund(session: Session, member: PoolMember, amount_cents: int) -> str:
    """Refund part of the member's charge and record it. Adds to member.refunded_cents."""
    if config.MOCK_PAYMENTS:
        ref = f"mock_re_{member.id}_{amount_cents}"
    else:
        ref = _stripe().Refund.create(
            payment_intent=_refundable_charge_ref(session, member, amount_cents), amount=amount_cents
        ).id
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
