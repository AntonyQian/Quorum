"""LLM-powered recommender (SPEC §6).

One LLM call per Wish: it parses the Wish and scores every live public Pool and every Hidden Listing.
`recommend` saves the Wish, records Demand Hits from hidden matches in the Price Band (never shown to the
shopper), and returns the SPEC §8 response; `complete` is the only function that talks to the model, so tests
stub it.
"""

import json

import openai
from pydantic import BaseModel, Field, ValidationError
from sqlmodel import Session, select

from app import config
from app.models import Pool, Product, User, Wish
from app.schemas import PoolSummary, Recommendation, RecommendResponse
from app.services import clock, demand, pool_engine, views
from app.services.wish_constraints import hidden_product_fit_score, merge_parsed_fields

MIN_DISPLAY_FIT_SCORE = 60
MIN_DEMAND_FIT_SCORE = 60
MAX_RECOMMENDATIONS = 6
MAX_SUGGESTIONS = 3


class RecommenderError(Exception):
    """The model could not produce a usable answer (API error, refusal, truncated or invalid output)."""


# --- structured output (SPEC §6 schema) ---------------------------------------


class ParsedWish(BaseModel):
    category: str | None = None
    budget_max_cents: int | None = None
    style_tags: list[str] = Field(default_factory=list)
    size_notes: str | None = None


class PoolMatch(BaseModel):
    pool_id: int
    fit_score: int = Field(ge=0, le=100)


class HiddenMatch(BaseModel):
    product_id: int
    fit_score: int = Field(ge=0, le=100)


class RecommenderOutput(BaseModel):
    parsed: ParsedWish
    pool_matches: list[PoolMatch]
    suggestions: list[PoolMatch] = Field(default_factory=list)
    hidden_matches: list[HiddenMatch]


# --- prompt -------------------------------------------------------------------

SYSTEM_PROMPT = """You are the shopping assistant for Quorum, a furniture group-buying site. Shoppers join \
Pools: the more people join before the deadline, the lower the price for everyone.

Given a shopper's Wish and the candidate items, return:
- parsed: what the shopper wants. category uses the same snake_case style as the candidates' categories \
(null if unclear); budget_max_cents is their maximum budget in integer US cents (null if not stated); \
style_tags are short lowercase materials or styles; size_notes is a short phrase about size or seating \
(null if none).
- pool_matches: ONLY public Pools that satisfy every constraint the shopper stated. If they gave a budget, \
the Pool's current_price_cents in the candidate JSON must be less than or equal to budget_max_cents. If \
they implied a category (parsed.category is set), the Pool's category must match. Each entry is pool_id \
and fit_score (0–100). Only include fit_score 60 or higher.
- suggestions: related Pools that miss at least one stated constraint (over budget, different category) but \
might still interest the shopper. pool_id and fit_score only; include only fit_score 60 or higher. Leave \
empty when nothing qualifies.
- hidden_matches: one entry per hidden listing that fits the Wish, with fit_score from 0 to 100. Only use \
product ids from the list.

Prices in the candidates are integer cents."""


def _pool_candidate(session: Session, pool: Pool) -> dict:
    summary = views.pool_summary(session, pool)
    product = session.get(Product, pool.product_id)
    candidate = {
        "id": pool.id,
        "name": product.name,
        "category": product.category,
        "style_tags": product.style_tags,
        "dimensions": product.dimensions,
        "status": pool.status,
        "current_price_cents": summary.current_price_cents,
        "participants": summary.participants,
        "deadline": summary.deadline,
    }
    if summary.next_tier:
        candidate["next_tier"] = {"needed": summary.next_tier.needed, "price_cents": summary.next_tier.price_cents}
    return candidate


def live_pools(session: Session) -> list[Pool]:
    pool_engine.evaluate_all(session)
    return list(session.exec(
        select(Pool)
        .join(Product, Product.id == Pool.product_id)
        .where(Pool.status.in_(pool_engine.LIVE), Product.visibility == "public")
        .order_by(Pool.deadline)
    ).all())


def hidden_listings(session: Session) -> list[Product]:
    return list(session.exec(select(Product).where(Product.visibility == "hidden").order_by(Product.id)).all())


def _hidden_candidate(product: Product) -> dict:
    return {
        "id": product.id,
        "name": product.name,
        "category": product.category,
        "style_tags": product.style_tags,
        "dimensions": product.dimensions,
        "floor_price_cents": product.floor_price_cents,
    }


def build_prompt(text: str, pool_candidates: list[dict], hidden_candidates: list[dict]) -> str:
    compact = {"separators": (",", ":"), "ensure_ascii": False}
    return (
        f"<wish>\n{text.strip()}\n</wish>\n\n"
        f"<public_pools>\n{json.dumps(pool_candidates, **compact)}\n</public_pools>\n\n"
        f"<hidden_listings>\n{json.dumps(hidden_candidates, **compact)}\n</hidden_listings>"
    )


# --- the LLM call ----------------------------------------------------------


def complete(prompt: str) -> RecommenderOutput:
    """The one LLM call on `OPENAI_MODEL` (structured output, minimal reasoning, no fallback model; SPEC §6).
    Raises RecommenderError on any failure."""
    try:
        client = openai.OpenAI(api_key=config.OPENAI_API_KEY or None)
        response = client.chat.completions.parse(
            model=config.OPENAI_MODEL,
            max_completion_tokens=16000,
            reasoning_effort="minimal",
            messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": prompt}],
            response_format=RecommenderOutput,
        )
    except openai.APIStatusError as e:
        raise RecommenderError(f"OpenAI API error ({e.status_code})") from e
    except openai.APIConnectionError as e:
        raise RecommenderError("Could not reach OpenAI") from e
    except (openai.OpenAIError, ValidationError, ValueError) as e:
        raise RecommenderError("The model returned an unusable answer") from e

    choice = response.choices[0]
    if choice.message.refusal:
        raise RecommenderError("The model declined this Wish")
    if choice.finish_reason != "stop" or choice.message.parsed is None:
        raise RecommenderError("The model returned an incomplete answer")
    return choice.message.parsed


# --- the use case -------------------------------------------------------------


def _product_for_pool(session: Session, pool: Pool) -> Product:
    return session.get(Product, pool.product_id)  # type: ignore[return-value]


def meets_stated_constraints(summary: PoolSummary, product: Product, parsed: ParsedWish) -> bool:
    """Hard gate for primary recommendations (budget and category when the Wish states them)."""
    if parsed.budget_max_cents is not None and summary.current_price_cents > parsed.budget_max_cents:
        return False
    if parsed.category is not None and product.category != parsed.category:
        return False
    return True


def _dedupe_ranked(
    matches: list[PoolMatch],
    pools_by_id: dict[int, Pool],
    min_score: int,
    limit: int,
    exclude: set[int] | None = None,
) -> list[PoolMatch]:
    skip = exclude or set()
    best: dict[int, PoolMatch] = {}
    for m in matches:
        if m.pool_id not in pools_by_id or m.pool_id in skip or m.fit_score < min_score:
            continue
        if m.pool_id not in best or m.fit_score > best[m.pool_id].fit_score:
            best[m.pool_id] = m
    return sorted(best.values(), key=lambda m: m.fit_score, reverse=True)[:limit]


def _partition_matches(
    session: Session,
    output: RecommenderOutput,
    pools_by_id: dict[int, Pool],
) -> tuple[list[PoolMatch], list[PoolMatch]]:
    """Enforce constraints in code so bad model output cannot surface as primary picks."""
    strict: list[PoolMatch] = []
    loose: list[PoolMatch] = []
    parsed = output.parsed

    for m in output.pool_matches + output.suggestions:
        pool = pools_by_id.get(m.pool_id)
        if pool is None:
            continue
        summary = views.pool_summary(session, pool)
        product = _product_for_pool(session, pool)
        bucket = strict if meets_stated_constraints(summary, product, parsed) else loose
        bucket.append(m)

    recommendations = _dedupe_ranked(strict, pools_by_id, MIN_DISPLAY_FIT_SCORE, MAX_RECOMMENDATIONS)
    rec_ids = {m.pool_id for m in recommendations}
    suggestions = _dedupe_ranked(
        loose, pools_by_id, MIN_DISPLAY_FIT_SCORE, MAX_SUGGESTIONS, exclude=rec_ids,
    )
    return recommendations, suggestions


def _to_recommendations(
    session: Session,
    matches: list[PoolMatch],
    pools_by_id: dict[int, Pool],
) -> list[Recommendation]:
    return [
        Recommendation(pool=views.pool_summary(session, pools_by_id[m.pool_id]))
        for m in matches
    ]


def in_price_band(match: HiddenMatch, product: Product, budget_max_cents: int | None) -> bool:
    """SPEC §6: a hidden match counts when the fit is high enough and the shopper's budget, if stated, reaches the
    Floor Price."""
    return match.fit_score >= MIN_DEMAND_FIT_SCORE and (
        budget_max_cents is None or budget_max_cents >= product.floor_price_cents)


def _deterministic_hidden_matches(
    text: str,
    parsed: ParsedWish,
    hidden: list[Product],
) -> list[HiddenMatch]:
    matches: list[HiddenMatch] = []
    parsed_dict = parsed.model_dump()
    for product in hidden:
        score = hidden_product_fit_score(text, parsed_dict, product)
        if score >= MIN_DEMAND_FIT_SCORE:
            matches.append(HiddenMatch(product_id=product.id, fit_score=score))
    return matches


def _merge_hidden_matches(
    llm_matches: list[HiddenMatch],
    deterministic: list[HiddenMatch],
) -> list[HiddenMatch]:
    best: dict[int, HiddenMatch] = {}
    for match in llm_matches + deterministic:
        if match.product_id not in best or match.fit_score > best[match.product_id].fit_score:
            best[match.product_id] = match
    return list(best.values())


def record_demand_hits(session: Session, user: User, wish: Wish, output: RecommenderOutput,
                       hidden_by_id: dict[int, Product]) -> None:
    """Turn hidden matches in the Price Band into Demand Hits (`demand` deduplicates and sends the alert)."""
    for match in output.hidden_matches:
        product = hidden_by_id.get(match.product_id)
        if product is not None and in_price_band(match, product, output.parsed.budget_max_cents):
            demand.add_demand_hit(session, product, user, wish)
    session.commit()


def recommend(session: Session, user: User, text: str) -> RecommendResponse:
    pools = live_pools(session)
    pools_by_id = {p.id: p for p in pools}
    hidden = hidden_listings(session)
    prompt = build_prompt(text, [_pool_candidate(session, p) for p in pools], [_hidden_candidate(p) for p in hidden])

    output = complete(prompt)
    merged = merge_parsed_fields(text, output.parsed.model_dump())
    output.parsed = ParsedWish.model_validate(merged)
    output.hidden_matches = _merge_hidden_matches(
        output.hidden_matches,
        _deterministic_hidden_matches(text, output.parsed, hidden),
    )

    wish = Wish(user_id=user.id, text=text, parsed=merged, created_at=clock.now(session))
    session.add(wish)
    session.commit()
    session.refresh(wish)
    record_demand_hits(session, user, wish, output, {p.id: p for p in hidden})

    rec_matches, suggestion_matches = _partition_matches(session, output, pools_by_id)

    return RecommendResponse(
        wish_id=wish.id,
        parsed=wish.parsed,
        recommendations=_to_recommendations(session, rec_matches, pools_by_id),
        suggestions=_to_recommendations(session, suggestion_matches, pools_by_id),
    )
