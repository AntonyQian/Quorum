"""Stripe mode of the payments adapter (SPEC §5), with the `stripe` SDK replaced by an in-memory fake so
no test touches the network."""

from datetime import timedelta
from types import SimpleNamespace

import pytest
from sqlmodel import select

from app import config
from app.models import Payment, Pool, PoolMember, Product, Retailer, Tier, User
from app.services import payments
from tests.conftest import T0, as_user, assert_error


class FakeCardError(Exception):
    def __init__(self, message, payment_intent_id=""):
        super().__init__(message)
        self.error = SimpleNamespace(payment_intent=SimpleNamespace(id=payment_intent_id) if payment_intent_id else None)


class FakeStripe:
    """Records every SDK call. Payment methods named in `failing_pms` decline when charged."""

    CardError = FakeCardError
    StripeError = Exception

    def __init__(self):
        self.api_key = None
        self.calls: list[tuple[str, dict]] = []
        self.failing_pms = {"pm_card_chargeCustomerFail"}
        self.checkout_sessions: dict[str, SimpleNamespace] = {}
        self._n = 0
        fake = self

        def rec(name, prefix, make=None):
            def call(*args, **kwargs):
                fake.calls.append((name, {"args": args, **kwargs}))
                fake._n += 1
                obj_id = f"{prefix}_{fake._n}"
                return make(obj_id, *args, **kwargs) if make else SimpleNamespace(id=obj_id, **kwargs)
            return call

        def make_checkout(obj_id, **kw):
            s = SimpleNamespace(id=obj_id, url=f"https://checkout.stripe.test/{obj_id}", setup_intent=None, **kw)
            fake.checkout_sessions[obj_id] = s
            return s

        def make_pi(obj_id, **kw):
            if kw["payment_method"] in fake.failing_pms:
                raise FakeCardError("Your card was declined.", payment_intent_id=obj_id)
            return SimpleNamespace(id=obj_id, status="succeeded", **kw)

        def attach(obj_id, pm, **kw):
            # Attaching a test token like pm_card_visa yields a new PaymentMethod that behaves like it.
            if pm in fake.failing_pms:
                fake.failing_pms.add(obj_id)
            return SimpleNamespace(id=obj_id, **kw)

        self.Customer = SimpleNamespace(create=rec("Customer.create", "cus"))
        self.PaymentMethod = SimpleNamespace(attach=rec("PaymentMethod.attach", "pm", attach))
        self.PaymentIntent = SimpleNamespace(create=rec("PaymentIntent.create", "pi", make_pi))
        self.Refund = SimpleNamespace(create=rec("Refund.create", "re"))
        self.checkout = SimpleNamespace(Session=SimpleNamespace(
            create=rec("checkout.Session.create", "cs", make_checkout),
            retrieve=self._retrieve,
        ))

    def _retrieve(self, session_id, **kwargs):
        self.calls.append(("checkout.Session.retrieve", {"args": (session_id,), **kwargs}))
        return self.checkout_sessions[session_id]

    def complete_setup(self, session_id, brand="visa", last4="4242", pm_id="pm_saved_1"):
        """What Stripe does when the shopper finishes Checkout: the session gets a succeeded SetupIntent."""
        s = self.checkout_sessions[session_id]
        s.setup_intent = SimpleNamespace(
            id="seti_1", status="succeeded",
            payment_method=SimpleNamespace(id=pm_id, card=SimpleNamespace(brand=brand, last4=last4)),
        )

    def named(self, name):
        return [kw for n, kw in self.calls if n == name]


@pytest.fixture
def fake_stripe(monkeypatch):
    fake = FakeStripe()
    monkeypatch.setattr(payments, "stripe", fake)
    monkeypatch.setattr(config, "MOCK_PAYMENTS", False)
    monkeypatch.setattr(config, "STRIPE_SECRET_KEY", "sk_test_fake")
    monkeypatch.setattr(config, "FRONTEND_URL", "http://front.test")
    return fake


def make_user(session, **kw):
    user = User(name=kw.pop("name", "Alice"), role="shopper", **kw)
    session.add(user)
    session.commit()
    return user


def test_setup_session_is_stripe_checkout_in_setup_mode_for_a_new_customer(session, fake_stripe):
    alice = make_user(session)

    url = payments.create_setup_session(session, alice, "/pools/3")

    [checkout] = fake_stripe.named("checkout.Session.create")
    assert url == checkout_url(fake_stripe)
    assert checkout["mode"] == "setup"
    assert checkout["success_url"] == "http://front.test/payment/success?session_id={CHECKOUT_SESSION_ID}"
    assert checkout["customer"] == alice.stripe_customer_id
    assert alice.stripe_customer_id.startswith("cus_")
    assert fake_stripe.api_key == "sk_test_fake"


def checkout_url(fake):
    [s] = fake.checkout_sessions.values()
    return s.url


# --- card saving through the API --------------------------------------------

def start_setup(client, user):
    url = client.post("/api/payments/setup-session", json={"return_to": "/pools/1"},
                      headers=as_user(user)).json()["url"]
    return url.rsplit("/", 1)[1]  # the fake's Checkout URL ends in the session id


def confirm(client, user, session_id):
    return client.post("/api/payments/confirm-setup", json={"session_id": session_id}, headers=as_user(user))


def test_confirm_setup_reads_the_card_off_the_checkout_session(client, session, fake_stripe):
    alice = make_user(session, card_declines=True)
    session_id = start_setup(client, alice)
    fake_stripe.complete_setup(session_id, brand="mastercard", last4="4444", pm_id="pm_alice")

    r = confirm(client, alice, session_id)

    assert r.status_code == 200, r.text
    assert r.json() == {"card_label": "Mastercard •••• 4444"}
    session.refresh(alice)
    assert alice.stripe_payment_method_id == "pm_alice"
    assert alice.card_declines is False
    assert client.get("/api/me", headers=as_user(alice)).json()["card_label"] == "Mastercard •••• 4444"


def test_confirm_setup_rejects_another_customers_checkout_session(client, session, fake_stripe):
    alice, mallory = make_user(session), make_user(session, name="Mallory")
    session_id = start_setup(client, alice)
    fake_stripe.complete_setup(session_id)

    assert_error(confirm(client, mallory, session_id), 400, "invalid_request")
    session.refresh(mallory)
    assert mallory.card_label is None


def test_confirm_setup_rejects_an_unfinished_checkout_session(client, session, fake_stripe):
    alice = make_user(session)
    session_id = start_setup(client, alice)

    assert_error(confirm(client, alice, session_id), 400, "invalid_request")


# --- Lock and Settlement against Stripe -------------------------------------

@pytest.fixture
def table_pool(session):
    """A $1,000 table Pool, Tier 1 at 3 ($100 off) and Tier 2 at 5 ($150 off), with 5 working-card Simulated
    Shoppers and the declining one. None of them has a Stripe customer yet."""
    oak = Retailer(name="Oak & Co.")
    session.add(oak)
    session.commit()
    session.add(User(name="Oak Admin", role="retailer", retailer_id=oak.id))
    session.add(User(name="Declining Dee", role="shopper", is_simulated=True, card_label="Visa •••• 4242",
                     card_declines=True))
    session.add_all([User(name=f"Sim {i}", role="shopper", is_simulated=True, card_label="Visa •••• 4242")
                     for i in range(5)])
    table = Product(retailer_id=oak.id, name="Walnut Table", category="dining_table", list_price_cents=100_000,
                    floor_price_cents=50_000, visibility="public", created_at=T0)
    session.add(table)
    session.commit()
    pool = Pool(product_id=table.id, opened_at=T0, deadline=T0 + timedelta(days=14))
    session.add(pool)
    session.commit()
    session.add_all([Tier(pool_id=pool.id, ordinal=1, min_participants=3, discount_cents=10_000),
                     Tier(pool_id=pool.id, ordinal=2, min_participants=5, discount_cents=15_000)])
    session.commit()
    return pool


def test_lock_to_settlement_charges_off_session_and_partially_refunds_on_stripe(client, session, fake_stripe,
                                                                               table_pool):
    pid = table_pool.id
    # The declining shopper joins first, so 4 join and Lock at Tier 1 ($900); the decline drops Dee.
    client.post(f"/api/demo/pools/{pid}/simulate-joins", json={"count": 3, "include_declining_card": True})
    # Two more join the locked Pool and are charged right away: the 4th at $900, the 5th reaches Tier 2 at $850.
    client.post(f"/api/demo/pools/{pid}/simulate-joins", json={"count": 2})
    # At the Deadline everyone pays $850, so the four who paid $900 get $50 Tier Refunds.
    client.post("/api/demo/clock/advance", json={"to_deadline_of_pool": pid})

    assert client.get(f"/api/pools/{pid}").json()["status"] == "completed"

    # Every Simulated Shopper got a test customer and a test card; Dee's declines on charge.
    attached = [kw["args"][0] for kw in fake_stripe.named("PaymentMethod.attach")]
    assert sorted(attached) == ["pm_card_chargeCustomerFail"] + ["pm_card_visa"] * 5
    assert len(fake_stripe.named("Customer.create")) == 6

    intents = fake_stripe.named("PaymentIntent.create")
    assert sorted(kw["amount"] for kw in intents) == [85_000, 90_000, 90_000, 90_000, 90_000, 90_000]
    assert all(kw["off_session"] is True and kw["confirm"] is True and kw["currency"] == "usd" for kw in intents)

    charges = session.exec(select(Payment).where(Payment.kind == "charge")).all()
    assert sorted((p.status, p.amount_cents) for p in charges) == [
        ("failed", 90_000), ("succeeded", 85_000),
        ("succeeded", 90_000), ("succeeded", 90_000), ("succeeded", 90_000), ("succeeded", 90_000)]
    early_pis = {p.provider_ref for p in charges if p.status == "succeeded" and p.amount_cents == 90_000}
    assert all(ref.startswith("pi_") for ref in early_pis)

    refunds = fake_stripe.named("Refund.create")
    assert sorted((kw["payment_intent"], kw["amount"]) for kw in refunds) == sorted((pi, 5_000) for pi in early_pis)
    refund_rows = session.exec(select(Payment).where(Payment.kind == "refund")).all()
    assert sorted(p.amount_cents for p in refund_rows) == [5_000] * 4
    assert all(p.status == "succeeded" and p.provider_ref.startswith("re_") for p in refund_rows)


def test_a_simulated_shoppers_stripe_customer_is_reused_across_charges(session, fake_stripe, table_pool):
    sim = session.exec(select(User).where(User.name == "Sim 0")).one()
    for amount in (1_000, 2_000):
        member = PoolMember(pool_id=table_pool.id, user_id=sim.id, joined_at=T0)
        session.add(member)
        session.commit()
        assert payments.charge(session, member, sim, amount)

    assert len(fake_stripe.named("Customer.create")) == 1
    assert len(fake_stripe.named("PaymentMethod.attach")) == 1


def test_a_real_shopper_without_a_stripe_card_is_declined_without_calling_stripe(session, fake_stripe, table_pool):
    bob = make_user(session, name="Bob", card_label="Visa •••• 4242")  # e.g. saved while in mock mode
    member = PoolMember(pool_id=table_pool.id, user_id=bob.id, joined_at=T0)
    session.add(member)
    session.commit()

    assert payments.charge(session, member, bob, 1_000) is False
    assert fake_stripe.named("PaymentIntent.create") == []
    assert session.exec(select(Payment)).one().status == "failed"
