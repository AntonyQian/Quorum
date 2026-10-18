# Quorum: Spec

> Group buying for big-ticket items. A discount unlocks only when enough shoppers commit together, and retailers can test demand for a product before they list it.

This file is the contract between the frontend (Cursor) and the backend (Claude Code). If you need to change an endpoint or a JSON shape, tell your teammate **before** you push the change here. Vocabulary comes from [GLOSSARY.md](GLOSSARY.md); the key decisions are in [docs/adr/](docs/adr/).

---

## 1. Concept

- **Shoppers** describe what they want in plain language (a **Wish**). Claude recommends live **Pools** and explains why each one fits.
- A **Pool** has 1–3 **Tiers**, for example "15 people: $200 off each" and "45 people: $250 off each". Shoppers **Join** by saving a card. They are not charged, and they can **Leave** freely.
- When the first Tier is reached, the Pool **Locks**: every Member is charged at once. More people can still join, and anyone who joins later is charged right away.
- At the **Deadline** (30 days at most) or when the **Stock Cap** is reached, the Pool settles. Everyone pays the same final price, and anyone who paid more gets an automatic **Tier Refund** for the difference.
- If the Pool never reaches Tier 1, nobody is charged (a **Failed Pool**).
- **Retailers** can list a Product publicly with a Pool, or as a **Hidden Listing**. Hidden Listings collect **Demand Hits** whenever a Shopper's Wish matches them within the **Price Band**. Once the **Demand Threshold** is reached, the retailer is alerted and can **Launch** a Pool. Every Shopper who matched it is notified.

**Track stages covered:** Payments (pooled, conditional charging and refunds), Checkout (synchronized group checkout), Discovery and Personalization (AI recommender), and Post-purchase (order and refund history).

---

## 2. Stack and repo layout

```
/                      SPEC.md, GLOSSARY.md, CLAUDE.md, docs/adr/, .cursor/rules/
/backend               Python 3.11+, FastAPI, SQLModel + SQLite, anthropic, stripe, uvicorn
/frontend              Next.js (App Router) + TypeScript + Tailwind (+ shadcn/ui)
```

- The backend runs on `http://localhost:8000`, with Swagger UI at `/docs` and the OpenAPI JSON at `/openapi.json`.
- The frontend runs on `http://localhost:3000`, and the backend allows it through CORS.
- Optional: run `npx openapi-typescript http://localhost:8000/openapi.json -o frontend/src/lib/api-types.ts` to generate TypeScript types from the backend.

### Environment variables

| Var | Where | Example |
|---|---|---|
| `ANTHROPIC_API_KEY` | backend | `sk-ant-...` |
| `CLAUDE_MODEL` | backend | `claude-sonnet-5-5` (use `claude-haiku-5-5` to save credits) |
| `MOCK_PAYMENTS` | backend | `true` skips Stripe entirely |
| `STRIPE_SECRET_KEY` | backend | `sk_test_...` (only when `MOCK_PAYMENTS=false`) |
| `FRONTEND_URL` | backend | `http://localhost:3000` (Stripe redirect target) |
| `NEXT_PUBLIC_API_URL` | frontend | `http://localhost:8000` |

---

## 3. Conventions (both sides)

- **Money is always integer cents** (`price_cents`). Only the frontend formats it as dollars.
- **Time is an ISO-8601 UTC string** taken from the **Sim Clock**, never from real time. The frontend shows countdowns using `time_left_seconds` from the API, not the browser clock.
- **Identity:** there is no login. The frontend sends `X-User-Id: <id>` on every request, and an account switcher in the top bar picks the user. Retailer endpoints return 403 for shopper accounts.
- **Errors:** a non-2xx response has the body `{"detail": {"code": "card_required", "message": "..."}}`. Error codes are listed below.
- **Live updates:** the frontend polls (pool detail and notifications every 3 seconds). There are no websockets.

Error codes: `card_required`, `pool_not_joinable`, `already_member`, `not_member`, `cannot_leave_locked`, `stock_cap_reached`, `not_found`, `forbidden`, `invalid_tiers`, `invalid_request`.

- A missing, malformed, or unknown `X-User-Id` on an endpoint that needs a user returns 401 `forbidden`. Endpoints that work anonymously (`GET /pools`, `GET /pools/{id}`) treat it as no user.
- A malformed path, query, or body returns 422 `invalid_request`, and an unknown route returns 404 `not_found`, in the same error body.
- Retailer products: `invalid_tiers` is 400 (any §4 Validation rule, including the 1–30 day Deadline and a stock cap below 1, and a PATCH whose prices would put a running Pool's Tier below the Floor Price). Other bad product input is 400 `invalid_request`: a Floor Price above the list price, `public` without a `pool`, `hidden` with a `pool`, or a PATCH that makes a Hidden Listing public (use Launch) or hides a Product whose Pool is open or locked. Another retailer's Product or Pool is 404 `not_found`.
- Join and Leave: `card_required` is 402 (also returned when Joining a locked Pool and the card is declined, in which case the Member becomes `payment_failed` and may Join again with another card; and in Stripe mode for a real shopper whose card was saved in mock mode). `pool_not_joinable`, `already_member`, `stock_cap_reached`, `not_member`, and `cannot_leave_locked` are 409. An unknown Pool is 404 `not_found`. Join checks the Pool before the card, so a user with no saved card gets `pool_not_joinable`, `already_member` or `stock_cap_reached` when one applies, and `card_required` only otherwise. `stock_cap_reached` applies when the stock cap is full but the Pool hasn't settled yet; a locked Pool whose cap is full is completed by `evaluate_pool`, so Joining it is `pool_not_joinable`.

---

## 4. Pool rules

### States

Hidden Listings are a **Product** visibility (`hidden`), not a Pool state. A Pool exists only once a Product is public.

```
open ──(members ≥ tier1)──▶ locked ──(deadline OR stock cap)──▶ completed
  │
  └──(deadline, members < tier1)──▶ failed
```

| Pool state | Join? | Leave? | Charged? |
|---|---|---|---|
| `open` | yes, card saved, no charge | yes | no |
| `locked` | yes, charged immediately at the current Tier price | no | yes |
| `completed` | no | no | settled, refunds issued |
| `failed` | no | no | nobody charged |

### Member statuses

`pending` (card saved, not charged yet; also a Member whose charge hit a payment-provider outage and will be retried), `charged`, `left`, `payment_failed` (card declined).
**Active members** are those that are `pending` or `charged`. The participant count shown everywhere is the number of active members.

### Pricing

- `tier_price(t) = list_price_cents - t.discount_cents`
- `current_tier` = the highest Tier with `min_participants <= active_count` (or none).
- Before the Pool Locks, "price if it locks" = Tier 1 price.
- `next_tier` = the lowest Tier above the current one; `needed = min_participants - active_count`.
- Validation: 1–3 Tiers, strictly increasing `min_participants` and `discount_cents`, and every `tier_price >= floor_price_cents`. Deadline between 1 and 30 days.

### `evaluate_pool(pool, now)`: the only place where Pool state changes

```
charge_pending(price):
    for m in pending members:
        outcome = payments.charge(session, m, m.user, price)
        succeeded   -> m.status = "charged"          # notify "Pool locked, you were charged"
        declined    -> m.status = "payment_failed"   # notify "Payment failed"
        unavailable -> m stays "pending"             # provider outage; retried on the next evaluation

if pool.status == "open":
    if active_count >= tiers[0].min_participants:
        pool.status = "locked"; pool.locked_at = now; notify retailer "Pool locked"
        charge_pending(tier_price(current_tier))
    elif now >= pool.deadline:
        pool.status = "failed"; notify all members "Pool didn't reach Tier 1, you were not charged"
elif pool.status == "locked":
    charge_pending(current_price)                    # late joiners, and Members left pending by an outage

if pool.status == "locked" and no pending members:
    if now >= pool.deadline or (pool.stock_cap and active_count >= pool.stock_cap):
        final = tier_price(current_tier)            # tier from charged count
        for m in charged members:
            owed = m.charged_cents - final - m.refunded_cents
            if owed > 0: payments.refund(session, m, owed)   # Tier Refund
        if any refund failed: stay locked            # the next evaluation retries only what is still owed
        else: pool.status = "completed"; pool.final_price_cents = final; notify members + retailer
```

- A locked Pool whose stock cap is full completes on its next `evaluate_pool`, so a Join on it gets `pool_not_joinable`; `stock_cap_reached` applies only while the cap is full and the Pool hasn't settled yet.
- Join on a `locked` Pool adds a `pending` Member and calls `evaluate_pool`, which charges them immediately at the current Tier price (after counting the new member). If the payment provider is unavailable, the Join still succeeds and the Member stays `pending` until a later evaluation charges them.
- Settlement waits while any Member is `pending` or any Tier Refund has failed, so a Pool can stay `locked` past its deadline during a payment-provider outage. Each charge and refund is committed as soon as it is made, and a refund is never issued twice.
- A card declined at Lock drops only that Member. The Pool still Locks even if the active count falls below Tier 1 as a result.
- Call `evaluate_pool` after every Join or Leave, whenever a Pool is read, and on every open or locked Pool after the clock is advanced.

---

## 5. Payments

Everything goes through one adapter, `services/payments.py`, with two implementations chosen by `MOCK_PAYMENTS`:

```
create_setup_session(session, user, return_to=None) -> url
confirm_setup(session, user, session_id) -> card_label   # "Visa •••• 4242"
has_usable_card(user) -> bool                            # Join checks this for card_required
charge(session, member, user, amount_cents) -> "succeeded" | "declined" | "unavailable"
refund(session, member, amount_cents) -> bool            # from the member's latest charge that covers it
```

`charge` and `refund` write every attempt to `payments` (status `succeeded` or `failed`, the provider's id in `provider_ref`) and update `member.charged_cents` / `member.refunded_cents` only on success. Neither commits; `evaluate_pool` does.

**Stripe mode** (test keys):
- Saving a card uses Stripe Checkout with `mode="setup"` and a Stripe Customer per user. `success_url = {FRONTEND_URL}/payment/success?session_id={CHECKOUT_SESSION_ID}`. The frontend then calls `confirm-setup`, and the backend reads the session's SetupIntent to get the payment method and stores it on the user. No webhooks.
- Charging uses a PaymentIntent with `off_session=True, confirm=True` on the saved payment method.
- Only a Stripe card error is a decline (`declined`: the Member becomes `payment_failed`). Any other Stripe error (network, rate limit, bad key) is `unavailable`: the attempt is recorded as a failed charge and the Member stays `pending`.
- Refunds use a Refund on the PaymentIntent with a partial `amount`. A Stripe error records a failed refund and returns false.
- Simulated Shoppers get a test customer with `pm_card_visa` attached, created on their first charge (so the first Lock in Stripe mode makes a few extra Stripe calls). One "declining" simulated shopper uses `pm_card_chargeCustomerFail`, which saves fine but fails when charged.
- Switching an existing database from mock to Stripe mode: refunding a charge made in mock mode (`provider_ref` starting `mock_`) is recorded as a mock refund without calling Stripe. A real shopper whose card was saved in mock mode has no Stripe payment method, so Join returns 402 `card_required` until they save a card again.

**Mock mode:** `create_setup_session` returns `{FRONTEND_URL}/payment/success?session_id=mock_<userId>`. `confirm_setup` stores `"Visa •••• 4242"` and clears `user.card_declines`, so a `payment_failed` Member can save a new card and Join again. `charge` succeeds unless `user.card_declines` is true. Refunds always succeed. Every charge and refund is still written to the `payments` table, so the UI looks the same in both modes.

---

## 6. AI recommender and demand

`POST /api/recommend` makes **one** Claude call (`CLAUDE_MODEL`, structured JSON output, low effort). The prompt includes:
- the Wish text
- a compact JSON list of **public Pools** (id, name, category, style tags, dimensions, current or next price, participants, deadline)
- a compact JSON list of **Hidden Listings** (id, name, category, style tags, dimensions, floor price), which the shopper never sees

The required output schema:

```json
{
  "parsed": { "category": "dining_table", "budget_max_cents": 80000, "style_tags": ["walnut", "mid-century"], "size_notes": "seats 4, small apartment" },
  "pool_matches":   [{ "pool_id": 12, "fit_score": 91, "reason": "Solid walnut, seats 4, $640 if it locks, 3 people from the next tier." }],
  "hidden_matches": [{ "product_id": 31, "fit_score": 84 }]
}
```

The backend then:
1. Saves the Wish (`wishes` table) with `parsed`.
2. Returns `pool_matches` with `fit_score >= 50`, sorted by score and capped at 6, joined with the Pool summaries.
3. For each hidden match with `fit_score >= 60` **and** (`budget_max_cents` is null **or** `>= floor_price_cents`), inserts a **Demand Hit** (unique per user and product).
4. If a Product's hit count has just reached its `demand_threshold`, it notifies the retailer: "23 shoppers want something like *Walnut Dining Table*. Launch a pool?"

On **Launch**, every user with a Demand Hit on that Product is notified with a link to the new Pool.

**Stretch:** `POST /api/retailer/products/{id}/suggest-tiers`, where Claude proposes tiers within the Price Band using the demand count.

---

## 7. Data model (SQLite)

```
retailers      id, name, tagline, logo_url
users          id, name, role ('shopper'|'retailer'), retailer_id?, is_simulated,
               card_label?, stripe_customer_id?, stripe_payment_method_id?, card_declines (bool)
products       id, retailer_id, name, description, category, style_tags (json), dimensions,
               image_url, list_price_cents, floor_price_cents,
               visibility ('hidden'|'public'), demand_threshold?, created_at
pools          id, product_id, status ('open'|'locked'|'completed'|'failed'),
               opened_at, deadline, stock_cap?, locked_at?, closed_at?, final_price_cents?
tiers          id, pool_id, ordinal (1-3), min_participants, discount_cents
pool_members   id, pool_id, user_id, status ('pending'|'charged'|'left'|'payment_failed'),
               joined_at, charged_cents (default 0), refunded_cents (default 0)
payments       id, pool_member_id, kind ('charge'|'refund'), amount_cents,
               status ('succeeded'|'failed'), provider_ref, created_at
wishes         id, user_id, text, parsed (json), created_at
demand_hits    id, product_id, user_id, wish_id, created_at      UNIQUE(product_id, user_id)
notifications  id, user_id, kind, title, body, link, read (bool), created_at
sim_clock      id=1, now
```

A user who leaves and re-joins reuses the same `pool_members` row (its status goes back to `pending`).

---

## 8. API

All routes are prefixed with `/api`. Shared shapes come first, then the endpoints.

### Shared shapes

```ts
type Tier = {
  ordinal: number; min_participants: number; discount_cents: number;
  price_cents: number;          // list_price - discount
  reached: boolean;
}

type ProductCard = {
  id: number; name: string; image_url: string; category: string;
  style_tags: string[]; retailer_name: string; list_price_cents: number;
}

type PoolSummary = {
  id: number;
  product: ProductCard;
  status: "open" | "locked" | "completed" | "failed";
  participants: number;                       // active members
  tiers: Tier[];
  current_price_cents: number;                // current Tier price, or Tier 1 price if none reached
  next_tier: { ordinal: number; needed: number; price_cents: number } | null;
  deadline: string; time_left_seconds: number;
  stock_cap: number | null;
}

type PoolDetail = PoolSummary & {
  product: ProductCard & { description: string; dimensions: string };
  my_membership: { status: "pending" | "charged" | "left" | "payment_failed";
                   charged_cents: number; refunded_cents: number } | null;
  final_price_cents: number | null;
}

type Notification = {
  id: number; kind: string; title: string; body: string;
  link: string | null;          // frontend route, e.g. "/pools/12"
  read: boolean; created_at: string;
}
```

### Accounts

| Method | Path | Body | Returns |
|---|---|---|---|
| GET | `/users` | none | `{id, name, role, retailer_id, card_label, is_simulated}[]` (for the switcher; simulated users are excluded unless `?include_simulated=true`) |
| GET | `/me` | none | the same user object |

### Shopper

| Method | Path | Body | Returns |
|---|---|---|---|
| GET | `/pools?status=open,locked&category=` | none | `PoolSummary[]` |
| GET | `/pools/{id}` | none | `PoolDetail` |
| POST | `/pools/{id}/join` | none | `PoolDetail`. Errors: `card_required`, `pool_not_joinable`, `already_member`, `stock_cap_reached` |
| POST | `/pools/{id}/leave` | none | `PoolDetail`. Errors: `cannot_leave_locked`, `not_member` |
| POST | `/recommend` | `{ text: string }` | `{ wish_id, parsed, recommendations: { pool: PoolSummary, fit_score: number, reason: string }[] }` |
| GET | `/me/orders` | none | `Order[]` (see below) |
| GET | `/me/notifications` | none | `{ unread: number, items: Notification[] }` |
| POST | `/notifications/{id}/read` | none | `{ ok: true }` |

```ts
type Order = {
  pool_id: number; product: ProductCard;
  pool_status: PoolSummary["status"];
  member_status: "pending" | "charged" | "left" | "payment_failed";
  charged_cents: number; refunded_cents: number; net_paid_cents: number;
  payments: { kind: "charge" | "refund"; amount_cents: number;
              status: "succeeded" | "failed"; created_at: string }[];
}
```

### Payments

| Method | Path | Body | Returns |
|---|---|---|---|
| POST | `/payments/setup-session` | `{ return_to?: string }` | `{ url }`. The frontend sends the browser there |
| POST | `/payments/confirm-setup` | `{ session_id }` | `{ card_label }`. 400 `invalid_request` (Stripe mode) when the session is unknown, belongs to another user, or card saving wasn't finished |

### Retailer (role must be `retailer`; scoped to the user's `retailer_id`)

| Method | Path | Body | Returns |
|---|---|---|---|
| GET | `/retailer/products` | none | `RetailerProduct[]` |
| POST | `/retailer/products` | `ProductCreate` | `RetailerProduct` |
| PATCH | `/retailer/products/{id}` | partial `ProductCreate` without `pool` | `RetailerProduct` |
| POST | `/retailer/products/{id}/launch` | `PoolCreate` | `PoolDetail` (Product becomes public, demand-hit shoppers notified) |
| GET | `/retailer/products/{id}/demand` | none | `{ total_hits, last_7_days, threshold, recent_wishes: { text, created_at }[] }` |
| GET | `/retailer/pools/{id}` | none | `PoolDetail & { members: { name, status, charged_cents, refunded_cents, joined_at }[], revenue_cents }` |
| GET | `/retailer/notifications` | none | the same as `/me/notifications` (alias) |

```ts
type PoolCreate = {
  deadline_days: number;                                 // 1–30
  stock_cap?: number | null;
  tiers: { min_participants: number; discount_cents: number }[];   // 1–3
}

type ProductCreate = {
  name: string; description: string; category: string; style_tags: string[];
  dimensions: string; image_url: string;
  list_price_cents: number; floor_price_cents: number;
  visibility: "hidden" | "public";
  demand_threshold?: number | null;      // hidden only
  pool?: PoolCreate;                     // required when visibility = "public"
}

type RetailerProduct = ProductCard & {
  visibility: "hidden" | "public";
  floor_price_cents: number;
  demand: { total_hits: number; last_7_days: number; threshold: number | null;
            threshold_reached: boolean } | null;    // hidden only
  pool: PoolSummary | null;                         // public only (latest pool)
}
```

### Demo panel (no role check)

| Method | Path | Body | Returns |
|---|---|---|---|
| GET | `/demo/clock` | none | `{ now }` |
| POST | `/demo/clock/advance` | `{ hours?: number, days?: number, to_deadline_of_pool?: number }` | `{ now }`, and it evaluates all open and locked Pools. The clock never goes back: negative `hours` or `days` is 400 `invalid_request`, and a deadline already passed leaves it where it is. Unknown `to_deadline_of_pool` is 404 `not_found` |
| POST | `/demo/pools/{id}/simulate-joins` | `{ count: number, include_declining_card?: boolean }` | `PoolDetail`. `count` is 0–200 (otherwise 422 `invalid_request`); unknown Pool is 404 `not_found` |
| POST | `/demo/products/{id}/simulate-demand` | `{ count: number }` | `{ total_hits }` (fake Wishes from simulated shoppers, no Claude call) |
| POST | `/demo/reset` | none | `{ ok: true }` (drop and reseed) |

---

## 9. Screens (frontend)

**Global top bar:** the Quorum logo, the account switcher (seeded users), a notification bell with an unread count, a Sim Clock readout, and a "Demo" button that opens the demo panel drawer.

**Shopper**
- `/`: a large "What are you looking for?" Wish box. When it has results, it shows AI recommendation cards (Pool card plus Claude's reason and a fit badge). Below that is a grid of all open and locked Pools, with category filter chips.
- `/pools/[id]`: product image and details, a **tier progress bar** (markers per Tier, filled to the participant count), "Next tier in N people", a countdown, the current price, and the Join or Leave button. When the Pool is locked, the button reads "Join (you'll be charged $X now)". If the user has no card, it starts the card-saving flow first.
- `/orders`: My Orders, with each order's charges and Tier Refunds as separate lines and a "You saved $X vs list price" summary.
- `/payment/success`: calls `confirm-setup`, then returns the user to `return_to`.

**Retailer**
- `/retailer`: dashboard with two tabs. **Live Pools** shows progress bars, status, and revenue. **Hidden Listings** shows a demand meter (hits / threshold, last 7 days) and a **Launch** button that glows when the threshold is reached.
- `/retailer/products/new`: the product form, with a visibility toggle (Public + Pool vs Hidden + Demand Threshold), a tier builder (up to 3 rows with a live price preview), a deadline slider (1–30 days), and a stock cap.
- Launch modal: the same tier builder plus deadline and stock cap fields, opened from Hidden Listings.
- `/retailer/pools/[id]`: member list with each member's status and charge or refund, and the pool's state history.

**Demo panel drawer:** advance clock (+1 day, +7 days, jump to a Pool's deadline), simulate joins (N, with or without a declining card), simulate demand (N), and reset.

---

## 10. Seed data (`backend/seed/seed.json`)

- **Retailers:** Oak & Co. (solid wood), Nordlund (modern Scandinavian), ReLoft (refurbished).
- **Accounts:** shoppers Alice and Bob (no saved card, so the card-saving flow can be shown), and one retailer login per retailer.
- **About 40 Simulated Shoppers**, all with cards saved. One has `card_declines = true`.
- **About 25 Products**, with Unsplash image URLs:
  - About 15 public, with open Pools at varied fill levels (some 2 people away from a Tier, one nearly at its deadline, one already locked, one completed with refunds so My Orders has history).
  - About 10 Hidden Listings with Demand Hits from 0 up to threshold−1. **"Walnut Dining Table" (Oak & Co.) must be at 9 of 10** for the demo.

---

## 11. Demo script (3 minutes)

1. **Retailer (Oak & Co.)** opens Hidden Listings: "Walnut Dining Table" shows **9 of 10** Demand Hits.
2. **Shopper Alice** types *"walnut dining table for 4, under $800"*. Claude recommends live Pools with reasons, and in the background this Wish becomes the **10th Demand Hit**.
3. **Retailer** sees the bell alert, then clicks **Launch** with Tiers **10 → $150 off** and **25 → $250 off** and a 14-day deadline.
4. **Alice** gets "The table you asked about is now a Pool". She joins and saves a card through Stripe test Checkout.
5. **Demo panel:** simulate 8 joins with a declining card. **Tier 1 is reached, the Pool locks, and everyone is charged at once** (show the Stripe dashboard). The declining card is dropped and notified.
6. Simulate 16 more joins to reach **Tier 2**, then jump to the deadline. The Pool **completes** and **$100 Tier Refunds** go out. **Alice's My Orders** shows the charge and the refund.

Closing line: *"Shoppers save by buying together; retailers only launch what people actually want."*

---

## 12. Ownership and timeline

| Hours | Frontend: Cursor | Backend: Claude Code |
|---|---|---|
| 0–2 | Next.js + Tailwind scaffold, top bar, account switcher, API client with **mock responses in the §8 shapes** | FastAPI scaffold, models, Sim Clock, seed loader, `GET /users`, `GET /pools`, `GET /pools/{id}` |
| 2–10 | Pool grid, pool detail with tier progress bar, Join/Leave, card-saving redirect, My Orders | `evaluate_pool` + unit tests, Join/Leave, payments adapter (mock first, then Stripe), orders, retailer product CRUD + Launch |
| 10–15 | Wish box + recommendation cards, retailer dashboard (both tabs), product form, Launch modal | `/recommend` with Claude, Demand Hits, threshold alerts, demand endpoint, notifications |
| 15–19 | Notification bell, demo panel, switch from mocks to the real API end to end | Demo endpoints, full seed data, fix integration bugs |
| 19–22 | Polish: loading states, empty states, animations on Lock and refund | Edge cases, Stripe mode run-through, rehearsing the demo flow |
| 22–24 | Together: rehearse the demo, record a backup video, write the Devpost entry, deploy only if everything is stable (Vercel + Render) |

**If behind schedule, cut in this order:** AI-suggested tiers → Stock Cap → declining-card example → "last 7 days" stats → notification bell (replace it with a banner on the next page load).

**Stretch goals, only if ahead:** suggested tiers, clustering Wishes with embeddings ([ADR 0002](docs/adr/0002-demand-hits-come-from-recommendation-calls.md)), deployment.

---

## 13. Out of scope

Real login, real money, shipping and tracking, returns, buying more than one unit, loyalty points, mobile apps, email or SMS, and multiple currencies.
