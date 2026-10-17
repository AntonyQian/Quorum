# One Sim Clock, and Pools are evaluated lazily instead of by a scheduler

Furniture Pools run for weeks, but the demo is 3 minutes. Every time-dependent rule reads "now" from a single Sim Clock stored in the database, which the demo panel can fast-forward. There are no cron jobs: `evaluate_pool` runs after every Join, Leave, and clock change and whenever a Pool is read, and it applies every state transition in one place.

## Consequences

- Code must never call `datetime.now()` directly for business logic.
- A Pool whose Deadline has passed only changes state when something touches it; the clock-advance endpoint evaluates every open or locked Pool so the demo never shows a stale state.
