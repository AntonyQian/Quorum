# Quorum

A group-buying marketplace for big-ticket items (furniture first) where a discount unlocks only when enough shoppers commit together, and where retailers can test demand for a product before listing it.

## People

**Shopper**:
A person browsing, asking for recommendations, and joining Pools.
_Avoid_: Customer, buyer, user (when the role matters)

**Retailer**:
A business that lists Products and launches Pools for them.
_Avoid_: Seller, vendor, company

**Simulated Shopper**:
A seeded Shopper controlled from the demo panel, used to fill Pools and generate Demand Hits during a demo.
_Avoid_: Bot, fake user

## Listings

**Product**:
A single item a Retailer offers, such as a specific dining table.
_Avoid_: Item, listing (on its own), SKU

**Hidden Listing**:
A Product the Retailer is willing to sell but has not made public; Shoppers never see it, but their Wishes can generate Demand Hits on it.
_Avoid_: Interested-to-sell, draft, private listing

**Public Listing**:
A Product with a live Pool that Shoppers can see and join.
_Avoid_: Live item, active listing

**List Price**:
The Product's normal, undiscounted price per unit.
_Avoid_: Base price, MSRP, full price

**Floor Price**:
The lowest per-unit price a Retailer will accept for a Product.
_Avoid_: Minimum price, reserve

**Price Band**:
The range from Floor Price to List Price; a Wish only counts as demand if the Shopper's budget reaches the Floor Price.
_Avoid_: Price range

## Pools

**Pool**:
A time-limited group offer on one Product, where the per-unit price drops as more Shoppers join.
_Avoid_: Deal, group buy, campaign, drop

**Tier**:
One step of a Pool's discount: a minimum number of Members and the amount off per unit once that number is reached. A Pool has one to three Tiers.
_Avoid_: Level, threshold (on its own), milestone

**Member**:
A Shopper who has joined a Pool with a saved card.
_Avoid_: Participant, backer, interested user

**Join**:
A Shopper's act of becoming a Member; before the Pool Locks, it costs nothing and can be undone by Leaving.
_Avoid_: Submit interest, pledge, reserve

**Lock**:
The moment a Pool reaches its first Tier; every Member is charged and nobody can Leave afterwards.
_Avoid_: Confirm, trigger, tip

**Settlement**:
The closing of a Locked Pool at its Deadline or Stock Cap, when the final Tier is fixed and every Member is refunded the difference between what they paid and the final price.
_Avoid_: Close-out, finalize

**Tier Refund**:
The automatic partial refund a Member receives at Settlement because the Pool reached a higher Tier than when they were charged.
_Avoid_: Rebate, cashback, credit

**Deadline**:
The time a Pool ends; at most 30 days after it opens.
_Avoid_: Expiry, timer, end date

**Stock Cap**:
An optional maximum number of Members a Pool accepts; reaching it triggers Settlement early.
_Avoid_: Inventory, limit

**Failed Pool**:
A Pool that reached its Deadline without Locking; nobody is charged.
_Avoid_: Cancelled pool, expired pool

## Demand

**Wish**:
A Shopper's plain-language description of what they want, entered in the recommendation box.
_Avoid_: Search, query, request

**Demand Hit**:
A record that one Shopper's Wish matched a Hidden Listing within its Price Band; counted at most once per Shopper per Product.
_Avoid_: Interest, signal, match (on its own)

**Demand Threshold**:
The number of Demand Hits at which a Retailer is alerted that a Hidden Listing is worth launching.
_Avoid_: Interest goal, trigger count

**Launch**:
A Retailer's act of turning a Hidden Listing into a Public Listing with a new Pool; Shoppers with Demand Hits on it are notified.
_Avoid_: Publish, go live, activate

## Demo

**Sim Clock**:
The single source of "now" for the whole app, which the demo panel can fast-forward.
_Avoid_: Server time, system time
