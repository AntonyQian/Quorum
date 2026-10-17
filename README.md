# Quorum

Say you want a walnut dining table that seats four, and the one you like costs $890. On Quorum it sits in a Pool with two Tiers: if 15 people join before the deadline, everyone pays $690, and if 45 join, everyone pays $640. Joining just means saving a card. You aren't charged, and you can leave whenever you want.

When the 15th person joins, the Pool Locks and every Member is charged $690 at the same moment. People can keep joining after that (they're charged right away), and if the count reaches 45 before the deadline, everyone who paid $690 gets $50 back automatically. If the Pool never reaches 15, nobody pays anything.

We built it for furniture first because that's where the math works. Nobody gets $200 off a $12 phone case, and a couch is a purchase people already wait on.

## Finding a Pool

You don't browse categories. You type what you want into one box ("something for a small apartment, under $800, I like mid-century") and Claude reads it, picks the live Pools that fit, and tells you why in a sentence: the wood, how many it seats, what it will cost if it locks, how many people it still needs.

## The retailer side

A retailer can launch a Pool on a product, or put the product up as a Hidden Listing. Shoppers never see Hidden Listings. But every time someone's request lines up with one and their budget reaches the retailer's lowest acceptable price, that counts as a Demand Hit. After enough of them the retailer gets an alert, and they can Launch a real Pool knowing people already asked for it. Everyone whose request matched gets a notification.

That's the part we were most curious about, honestly. Retailers get to see demand for a product before they commit to selling it, and shoppers get to tell them they want it just by describing what they're looking for. We haven't figured out how many Demand Hits should count as "enough." Right now the retailer picks a number for each Hidden Listing.

## In the repo

- [SPEC.md](SPEC.md): the full spec, and the API contract between frontend and backend
- [GLOSSARY.md](GLOSSARY.md): what Pool, Tier, Lock, Settlement and the rest mean here
- [docs/adr/](docs/adr/): the decisions we made and why
- [Issues](https://github.com/AntonyQian/Quorum/issues): the build tickets, in dependency order

The backend is FastAPI with SQLite, and the frontend is Next.js. Payments run through Stripe in test mode, or a mock if you set `MOCK_PAYMENTS=true`. There's also a demo panel that fast-forwards the clock and fills Pools with simulated shoppers, because nobody is waiting 30 days to watch a deadline pass.
