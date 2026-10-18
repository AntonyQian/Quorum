# Demand Hits are a byproduct of the recommendation call

Retailers need to know whether a Hidden Listing would sell before launching it. Instead of a separate demand-sensing pipeline, the same LLM call that ranks public Pools for a Shopper's Wish also scores Hidden Listings; a match whose Shopper budget reaches the Floor Price is stored as a Demand Hit (at most one per Shopper per Product). Hidden Listing matches are never returned to the Shopper.

## Considered Options

- **Cluster all Wishes with embeddings and match clusters to Products**: more accurate at scale and more "ML", but too much to build first in 24 hours. It stays a stretch goal and can replace the matching step later without changing the Demand Hit model.

## Consequences

- Demand only accumulates when Shoppers use the recommendation box, so the demo panel can generate Demand Hits directly.
