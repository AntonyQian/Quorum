"""Payments adapter (SPEC §5). Mock or Stripe, chosen by MOCK_PAYMENTS.

Every charge and refund is written to the `payments` table. Stripe mode uses test keys and no webhooks:
Checkout in setup mode saves a card on a Customer, Lock charges are off-session PaymentIntents, and Tier
Refunds are partial Refunds on the charge's PaymentIntent.
"""

import logging

import stripe
from sqlmodel import Session, select

from app import config
from app.errors import api_error
from app.models import Payment, PoolMember, User
from app.services import clock


logger = logging.getLogger(__name__)

CURRENCY = "usd"
SIM_WORKING_CARD = "pm_card_visa"
SIM_DECLINING_CARD = "pm_card_chargeCustomerFail"  # Stripe test card: attaches fine, fails when charged
WORKING_CARD_LABEL = "Visa •••• 4242"  # mock mode's saved card, and every Simulated Shopper's
DECLINING_CARD_LABEL = "Visa •••• 0341"  # a declining Simulated Shopper created by simulate-joins
MOCK_REF_PREFIX = "mock_"

# charge() outcomes
SUCCEEDED = "succeeded"
DECLINED = "declined"  # a card problem: the Member ends payment_failed
UNAVAILABLE = "unavailable"  # the provider failed (network, config, outage): the Member stays pending


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
        currency=CURRENCY,
        payment_method_types=["card"],
        success_url=_frontend_url("/payment/success?session_id={CHECKOUT_SESSION_ID}"),
        cancel_url=_frontend_url(return_to or "/"),
    )
    return checkout.url


def confirm_setup(session: Session, user: User, session_id: str) -> str:
    if config.MOCK_PAYMENTS:
        user.card_label = WORKING_CARD_LABEL
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


def has_usable_card(user: User) -> bool:
    """Whether `user` has a card the current payments mode can charge. In Stripe mode a real shopper needs a
    card saved through Stripe; one saved while in mock mode has only a label, so they must save it again."""
    if not user.card_label:
        return False
    return config.MOCK_PAYMENTS or user.is_simulated or bool(user.stripe_payment_method_id)


def _ensure_simulated_card(session: Session, user: User) -> None:
    """Give a Simulated Shopper a Stripe test customer and test card the first time they are charged.
    The declining one gets a card that saves fine but fails when charged."""
    if user.stripe_payment_method_id:
        return
    token = SIM_DECLINING_CARD if user.card_declines else SIM_WORKING_CARD
    customer_id = _ensure_customer(session, user)
    user.stripe_payment_method_id = _stripe().PaymentMethod.attach(token, customer=customer_id).id
    session.add(user)


def _stripe_charge(session: Session, member: PoolMember, user: User, amount_cents: int) -> tuple[str, str]:
    """(outcome, PaymentIntent id). Only a card error is a decline; any other Stripe error is UNAVAILABLE."""
    try:
        if user.is_simulated:
            _ensure_simulated_card(session, user)
        if not (user.stripe_customer_id and user.stripe_payment_method_id):
            return DECLINED, ""  # no card saved through Stripe; Join refuses these, see has_usable_card
        intent = _stripe().PaymentIntent.create(
            amount=amount_cents,
            currency=CURRENCY,
            customer=user.stripe_customer_id,
            payment_method=user.stripe_payment_method_id,
            off_session=True,
            confirm=True,
            metadata={"quorum_pool_member_id": str(member.id)},
        )
    except stripe.CardError as exc:
        failed = getattr(exc.error, "payment_intent", None)
        return DECLINED, getattr(failed, "id", "") or ""
    except stripe.StripeError:
        logger.exception("Stripe charge for Pool Member %s failed", member.id)
        return UNAVAILABLE, ""
    return (SUCCEEDED if intent.status == "succeeded" else DECLINED), intent.id


def charge(session: Session, member: PoolMember, user: User, amount_cents: int) -> str:
    """Charge the member's card and record the attempt. Returns SUCCEEDED, DECLINED (a card problem) or
    UNAVAILABLE (the provider failed; try again later). Adds to member.charged_cents on success."""
    if config.MOCK_PAYMENTS:
        outcome = DECLINED if user.card_declines else SUCCEEDED
        ref = f"mock_ch_{member.id}_{amount_cents}" if outcome == SUCCEEDED else ""
    else:
        outcome, ref = _stripe_charge(session, member, user, amount_cents)
    _record(session, member, "charge", amount_cents, outcome == SUCCEEDED, ref)
    if outcome == SUCCEEDED:
        member.charged_cents += amount_cents
        session.add(member)
    return outcome


def _refundable_charge(session: Session, member: PoolMember, amount_cents: int) -> Payment | None:
    """The member's latest succeeded charge large enough to cover the Tier Refund."""
    return session.exec(
        select(Payment)
        .where(Payment.pool_member_id == member.id, Payment.kind == "charge", Payment.status == "succeeded",
               Payment.amount_cents >= amount_cents)
        .order_by(Payment.id.desc())
    ).first()


def _stripe_refund(session: Session, member: PoolMember, amount_cents: int) -> tuple[bool, str]:
    original = _refundable_charge(session, member, amount_cents)
    if original is None:
        logger.error("Pool Member %s has no charge to refund %s cents from", member.id, amount_cents)
        return False, ""
    if original.provider_ref.startswith(MOCK_REF_PREFIX):  # charged in mock mode: no money moved
        return True, f"mock_re_{member.id}_{amount_cents}"
    try:
        return True, _stripe().Refund.create(payment_intent=original.provider_ref, amount=amount_cents).id
    except stripe.StripeError:
        logger.exception("Stripe refund for Pool Member %s failed", member.id)
        return False, ""


def refund(session: Session, member: PoolMember, amount_cents: int) -> bool:
    """Refund part of the member's charge and record the attempt. Adds to member.refunded_cents on success;
    a failed refund changes nothing else, so the caller can retry what is still owed."""
    if config.MOCK_PAYMENTS:
        ok, ref = True, f"mock_re_{member.id}_{amount_cents}"
    else:
        ok, ref = _stripe_refund(session, member, amount_cents)
    _record(session, member, "refund", amount_cents, ok, ref)
    if ok:
        member.refunded_cents += amount_cents
        session.add(member)
    return ok


def _record(session: Session, member: PoolMember, kind: str, amount_cents: int, ok: bool, ref: str) -> None:
    session.add(
        Payment(
            pool_member_id=member.id,
            kind=kind,
            amount_cents=amount_cents,
            status="succeeded" if ok else "failed",
            provider_ref=ref,
            created_at=clock.now(session),
        )
    )
