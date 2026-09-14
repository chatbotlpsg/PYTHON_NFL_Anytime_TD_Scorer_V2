from __future__ import annotations

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class QuotaPlan:
    events: int
    opportunity_cost: int
    mainline_cost: int
    production_cost: int
    reprice_cost: int
    planned_max: int


def bookmaker_groups(bookmakers: list[str]) -> int:
    return max(1, math.ceil(len(bookmakers) / 10))


def estimate_plan(events: int, opportunity_markets: int, production_markets: int, shortlist_events: int,
                  reprice_market_families: int, bookmakers: list[str]) -> QuotaPlan:
    groups = bookmaker_groups(bookmakers)
    opportunity = events * opportunity_markets * groups
    mainlines = 3 * groups
    production = shortlist_events * production_markets * groups
    reprice = shortlist_events * reprice_market_families * groups
    return QuotaPlan(events, opportunity, mainlines, production, reprice,
                     opportunity + mainlines + production + reprice)


def assert_reserve(current_remaining: int | None, estimated_cost: int, reserve: int) -> None:
    if current_remaining is None:
        return
    if current_remaining - estimated_cost < reserve:
        raise RuntimeError(
            f"BLOCKED_BY_QUOTA_GOVERNOR: remaining={current_remaining} planned={estimated_cost} reserve={reserve}"
        )
