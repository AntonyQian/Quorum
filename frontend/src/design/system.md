# Quorum design system

Showroom, not a coupon site. Quorum is a group-buying marketplace for furniture. The interface should feel like a well-lit room: warm paper, walnut ink, one forest green for price and action. Pool status never borrows the brand green.

Screens import recipes from [`tokens.ts`](./tokens.ts). Do not paste a new hex color, font size, or status sentence into a component. If a screen needs a treatment that is not here, add the token first, then use it.

## Principles

1. **One price color.** The price in effect is forest (`typeScale.price`, or `typeScale.priceLead` when a Next Tier sits under it). The Next Tier price is `typeScale.next`: smaller, walnut, not forest. List price, when a discount is already in effect, is `typeScale.compare`.
2. **Money is cents until the edge.** Call `formatCents` from `src/lib/money.ts`. Never divide by 100 in a component.
3. **The Sim Clock is the only clock.** Countdowns render `time_left_seconds` with `formatTimeLeft`. The top bar renders the API timestamp with `formatSimClock`. Do not call `Date.now()` to tick a Deadline.
4. **Glossary words in the interface.** Pool, Tier, Member, Lock, Deadline, Tier Refund, Sim Clock, Shopper, Retailer. The count on a card is "8 Members", even though the API field is `participants`.
5. **Status has one sentence.** Each Pool state has a label, a badge class, and a note in `poolStatus`. Use that note on the detail page. Do not invent a second explanation.
6. **Compose, don't restyle shadcn.** Buttons, cards, badges, and menus come from `src/components/ui`. Quorum color and type reach them through the CSS variables below.

## Color

Defined on `:root` in `src/app/globals.css` and registered for Tailwind in `@theme`.

| Token | Role |
|---|---|
| `--background` | Warm paper. Page and top bar. |
| `--foreground` | Walnut ink. Body text and the wordmark. |
| `--card` | White card surface, slightly warmer than pure white. |
| `--primary` | Forest green. Current price, filled progress, selected chip, primary button. |
| `--primary-foreground` | Text on forest. |
| `--secondary` | Quiet chip and toolbar surface. |
| `--muted` | Progress track, skeletons, footer bands. |
| `--muted-foreground` | Meta text: retailer, Member count, Deadline. |
| `--border` | Hairline under the top bar and around controls. |
| `--destructive` | Errors only. Not for a Failed Pool. |
| `--status-open` | Open. Tailwind: `bg-status-open`, `text-status-open`. |
| `--status-locked` | Locked. Amber, distinct from Open. |
| `--status-completed` | Completed. Slate, quiet. |
| `--status-failed` | Failed. Clay, distinct from `--destructive`. |

Badge classes live on `poolStatus[status].badge`. They are solid status fills so the label stays readable on a photograph. They are the only place status color classes are written.

## Type

Geist Sans is `--font-sans` and `--font-heading`. Geist Mono is `--font-mono`, reserved for money-in-cents while debugging, not for prices Shoppers read.

| Recipe | Use |
|---|---|
| `typeScale.wordmark` | "Quorum" in the top bar. |
| `typeScale.display` | Pool name on the detail page. |
| `typeScale.title` | Card title. |
| `typeScale.price` | A discount price: the price in effect, or the next Tier price when no Tier has been reached. |
| `typeScale.priceLead` | The price in effect when a Next Tier is also on screen. Larger than `typeScale.price`, still forest. |
| `typeScale.next` | The following Tier price. Walnut, one step down from the price in effect. |
| `typeScale.list` | List price when no Tier has been reached yet. |
| `typeScale.compare` | List price when a discount is already in effect. |
| `typeScale.savings` | How much a reached Tier takes off the list price, e.g. "$80.00 off". |
| `typeScale.meta` | Retailer, Member count, time left. |
| `typeScale.eyebrow` | Section labels: "Current price", "Tiers", "Time left", "Sim Clock". Uppercase, tracked out. |

## Space and layout

| Recipe | Use |
|---|---|
| `layout.page` | The column under the top bar. Max width 72rem, `px-3 py-4`, vertical rhythm of `gap-5`. |
| `layout.topBar` | Sticky bar, paper at 90% with blur, hairline border. |
| `layout.topBarInner` | Bar contents, same max width as the page, height 2.75rem, `px-3`. |
| `layout.grid` | Pool cards. One column, two from `sm`, three from `lg`, gap 0.75rem. |
| `layout.cluster` | Chip rows. |
| `layout.stack` | Detail page sections. |
| `skeleton` | Loading blocks. Pulse on `--muted`. |

Cards use the shadcn `Card` with `--card-spacing` set to `0.5rem`. Hover adds `shadow-md`. Product images are 4:3, `object-cover`, full bleed at the top of the card. The product name and retailer sit in `glass.pill` on the photo, inset from the bottom-left corner. The detail image is 16:9. Open and Locked do not get a status chip. Completed and Failed still do, so a settled card stays readable.

## Radius, elevation, motion

Radius comes from shadcn `--radius` (0.75rem). Chips are full pills (`rounded-full`). Do not introduce a second radius scale.

Elevation is flat: cards use the shadcn ring, and only the hovered card lifts (`shadow-md`). No drop shadows on the top bar.

Motion is color and shadow only, `transition-colors` / `transition-shadow`, plus the Lock and completion moment below (a short fade-in and a ring). Do not animate the countdown. Pool detail refreshes by polling every `POLL_INTERVAL_MS` (3000). The number on screen changes when the response changes.

## Pool status

| State | Label | What the Shopper should understand |
|---|---|---|
| `open` | Open | Join is free until Lock. |
| `locked` | Locked | Members are charged. A higher Tier can still lower the price. |
| `completed` | Completed | Settled at the final Tier price. |
| `failed` | Failed | Tier 1 was missed. Nobody was charged. |

The grid has two scopes in `poolScopes`:

- **Live** (default): `open` and `locked`. This is the shopper home.
- **Settled**: `completed` and `failed`, so every state has a card and a detail page.

Category chips use `chip`. `chip.selected` is forest. `chip.idle` is secondary. "All" clears the category. Chip labels come from `categories` via `categoryLabel`.

## Tiers

The card and the detail price block use `DiscountOffer`.

- Every live Pool uses the same two blocks. "Now" is `typeScale.priceLead`: the price in effect, with the list struck through once a Tier is reached. No "$X off" line. Under a hairline, "Next Tier" and the following price share one row (`justify-between`), then the progress bar, then the quietest line: "N more Members · 1 day left" on the card (`formatTimeLeftWords`).
- No Tier reached yet: "Now" is the list price. "Next Tier" is the first Tier.
- Top Tier or Completed: the discount in effect, then "Top Tier reached" or "Settled", bar full. No "$X off" line.
- Failed: list price, "This Pool didn't reach Tier 1", and `bar.fillMuted` for how close Tier 1 was.

`bar.track` is the muted rail. `bar.fill` is forest. On the detail page, `TierProgressBar` is the full ladder: width = Member count / scale, scale is the Stock Cap when there is one, otherwise the last Tier's `min_participants`. `bar.markerReached` sits on a reached Tier. `bar.marker` sits on a Tier still ahead.

## Money and time

| Helper | Module | Example |
|---|---|---|
| `formatCents(64000)` | `src/lib/money.ts` | `$640.00` |
| `formatTimeLeft(172800)` | `src/lib/pools.ts` | `2d 0h` |
| `formatTimeLeftWords(86400)` | `src/lib/pools.ts` | `1 day` |
| `formatSimClock(iso)` | `src/lib/pools.ts` | `Oct 17, 2026, 9:00 PM UTC` |
| `memberCountLabel(8)` | `tokens.ts` | `8 Members` |
| `roleLabel("shopper")` | `tokens.ts` | `Shopper` |

A live Deadline on the detail page reads `{formatTimeLeft} left`. On a card, the Next Tier line reads `{membersAwayLabel} · {formatTimeLeftWords} left`, for example "8 more Members · 1 day left". `Ended` stands alone.

## Chrome

The top bar, left to right:

1. Wordmark, links home.
2. Spacer.
3. Sim Clock readout: eyebrow "Sim Clock", then `formatSimClock`. It re-reads `GET /demo/clock` after every Demo action.
4. "My Orders" ghost link. Hidden for Retailer accounts.
5. Notification bell. Placeholder: icon button, unread count if `unread > 0` (polled every `POLL_INTERVAL_MS`), no menu.
6. Demo button. Outline button that opens the Demo drawer.
7. Account switcher. Outline menu of `listUsers()` (Simulated Shoppers excluded). The choice is stored under `quorum-user-id` and sent as `X-User-Id` on every request. With nothing stored, or a stored id that no longer exists, it starts as the first Shopper.

### Demo drawer

`demo.panel` slides in from the right over `demo.backdrop`. Labels wrap their control in `demo.field`, and number inputs and selects use `demo.input`. Sections are `demo.section`: Sim Clock (+1 day, +7 days, Jump to Deadline), Pool (picker of live Pools, defaulting to the Pool on screen), Simulate joins (count, optional declining card), Simulate demand (a Retailer picks one of their Hidden Listings; anyone else types a Product id), and Reset. After each action the drawer calls `refresh()` on the account context, which re-reads the Sim Clock and bumps `dataVersion` so screens refetch. Errors show the server's message, because the presenter is the reader.

## Join, Leave, and the card-saving flow

The Join panel (`memberPanel.box`) sits under the price on the detail page. `joinAction` in `src/lib/membership.ts` picks the button: "Join" on an open Pool, "Leave" for its Members, "Join (you'll be charged $X now)" on a locked Pool, nothing once settled. A Retailer sees "Switch to a Shopper account to Join." `card_required` stores the Pool in `sessionStorage` (`src/lib/card-flow.ts`) and sends the browser to the setup-session URL. `/payment/success` confirms the card, finishes the Join, and returns to the Pool. Other error codes become sentences through `friendlyError` in `src/lib/errors.ts`.

## Member line and moments

Every Pool state shows its `StatusBadge` on the detail page, with `poolStatus[status].note` under the Tiers. `membershipMessage` gives the active account one sentence (`memberPanel.line`) that includes what they were charged, any Tier Refund, and the net paid. When polling sees a Pool change to locked or completed, `poolMoment[status]` plays for `MOMENT_MS`: its `text` in its `banner`, and its `ring` around the price block, both in the status color. `momentRest` is the transparent ring the block returns to. Besides `poolStatus[status].badge`, `poolMoment` is the only place status color classes are written. The Member line is `memberPanel.line`, and errors under the Join button are `memberPanel.error`. Errors elsewhere (the Demo drawer, My Orders) use `memberPanel.error` too.

## My Orders

`/orders` lists `GET /me/orders`. Each order is a card: photo, name, `StatusBadge`, retailer and `memberStatusLabel`, then each charge and Tier Refund on its own line with its Sim Clock date (failed attempts in `failedAmount`), then "Net paid" in `typeScale.price`. The heading carries "You saved $X vs list price" (`totalSavingsCents` in `src/lib/orders.ts`) in `typeScale.savings`.

## Copy

- Empty category: "No Pools in this category."
- Empty scope: "No Pools here yet."
- Missing Pool: "This Pool is not available."
- Load failure: "Couldn't load Pools." with a Retry button.
- Back link on detail: "All Pools", in `textLink` like every in-page text link.
- Section eyebrows: "Now", "Next Tier", "List", "Tiers", "Time left".
- Distance to a Tier, on a card with time left: "8 more Members · 1 day left". "1 more Member" when only one person is missing. The detail page shows the distance without the Deadline, because Time left is its own section.
- Member line, when `my_membership` is set: `membershipMessage`, for example "You are a Member. You were charged $519.00." or "You were charged $519.00 and got a $70.00 Tier Refund, so you paid $449.00."
- Empty My Orders: "No orders yet." with a "Browse Pools" link.

## Adding a screen

1. Read this file and use an existing recipe.
2. If the screen needs a new pattern, add it to `tokens.ts` and a row in this file in the same change.
3. Keep API access in `src/lib/api.ts`. Set `NEXT_PUBLIC_USE_MOCKS=true` to use the mocks.
