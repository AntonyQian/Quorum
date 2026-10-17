# Charge at Lock, refund the Tier difference at Settlement

Shoppers must feel safe joining (no charge if the Pool fails), retailers must be guaranteed the sale the moment the first Tier is reached, and higher Tiers must still be reachable afterwards. We save cards on Join without charging, charge every Member the current Tier price at Lock (and later joiners at the then-current price), and at Settlement automatically refund each Member down to the final Tier price.

## Considered Options

- **Lock at Tier 1 but charge at the Deadline**: simpler, but a 30-day furniture Pool would leave the "sale" unpaid for weeks and saved cards can fail by then.
- **Charge at Tier 1 and close the Pool**: drops the higher Tiers entirely.
- **Authorize-and-capture card holds**: holds expire after about 7 days, which is too short for a 30-day Deadline.

## Consequences

- A Member may pay one price and be refunded later; My Orders must show charges and Tier Refunds as separate lines.
- A card declined at Lock drops only that Member; the Pool still Locks for everyone else.
