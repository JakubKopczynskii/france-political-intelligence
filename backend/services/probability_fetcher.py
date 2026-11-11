"""
Fetches political scenario probabilities from Polymarket prediction market API.
No API key required — Polymarket is a public prediction market.

What data leaves the machine: an HTTP GET request with query params
{"tag": "france", "limit": 50} is sent to gamma-api.polymarket.com.
No user data, portfolio data, or scenario edits are sent.

If Polymarket is unavailable or returns no matching French political markets,
the function returns None and existing DB probabilities are left unchanged.
This is a best-effort enrichment, not a hard dependency.

Methodology note:
  Prediction market prices (0–1) represent the crowd's aggregate probability
  estimate for a binary event. They are not official forecasts.
  When Polymarket data is used, probability_label is updated to reflect the source.
  When no data is found, illustrative analyst inputs remain in place.
"""
import json
from typing import Optional
from sqlalchemy.orm import Session

try:
    import aiohttp
    _AIOHTTP_AVAILABLE = True
except ImportError:
    _AIOHTTP_AVAILABLE = False

from models import PoliticalScenario

POLYMARKET_API = "https://gamma-api.polymarket.com/markets"

# Keyword lists used to match Polymarket market titles to our 4 scenarios.
# A market matches if ANY of its keywords appear in the question text (case-insensitive).
SCENARIO_POLYMARKET_KEYWORDS: dict = {
    "centrist": ["macron", "centrist", "ensemble", "moderate france", "renaissance"],
    "national_rally": ["le pen", "rassemblement national", "national rally", "bardella", "rn "],
    "left_wing": ["nfp", "left coalition", "gauche", "nupes", "mélenchon", "melenchon", "lfi"],
    "hung_parliament": ["hung", "deadlock", "no majority", "paralysis", "fragmented assembly"],
}


async def fetch_polymarket_probs() -> Optional[dict]:
    """
    Try to fetch French political market prices from Polymarket.
    Returns {scenario_slug: probability} normalized to sum=1, or None on failure.
    """
    if not _AIOHTTP_AVAILABLE:
        return None

    try:
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=10)
        ) as session:
            params = {"tag": "france", "limit": 50, "active": "true"}
            async with session.get(POLYMARKET_API, params=params) as resp:
                if resp.status != 200:
                    return None
                markets = await resp.json(content_type=None)
    except Exception:
        return None

    if not markets:
        return None

    raw_probs: dict = {}
    for scenario_slug, keywords in SCENARIO_POLYMARKET_KEYWORDS.items():
        for market in markets:
            title = (market.get("question") or market.get("title") or "").lower()
            if any(kw in title for kw in keywords):
                try:
                    prices = json.loads(market.get("outcomePrices") or "[]")
                    if prices:
                        raw_probs[scenario_slug] = float(prices[0])
                        break
                except (ValueError, TypeError, json.JSONDecodeError):
                    pass

    # Need at least 2 scenario matches to be worth using
    if len(raw_probs) < 2:
        return None

    # Fill missing scenarios with equal share of remaining probability
    matched = set(raw_probs.keys())
    all_slugs = ["centrist", "national_rally", "left_wing", "hung_parliament"]
    missing = [s for s in all_slugs if s not in matched]
    if missing:
        total_found = sum(raw_probs.values())
        remainder = max(0.0, 1.0 - total_found)
        for slug in missing:
            raw_probs[slug] = max(0.05, remainder / len(missing))

    # Normalize to sum exactly 1
    total = sum(raw_probs.values())
    if total <= 0:
        return None
    return {k: round(v / total, 4) for k, v in raw_probs.items()}


async def refresh_scenario_probabilities(db: Session) -> int:
    """
    Try to update scenario probabilities from Polymarket prediction markets.
    Returns number of scenarios updated (0 if Polymarket data unavailable).
    Existing probabilities are NEVER deleted — only updated when data is found.
    """
    probs = await fetch_polymarket_probs()
    if not probs:
        return 0

    count = 0
    for slug, prob in probs.items():
        scenario = db.query(PoliticalScenario).filter(
            PoliticalScenario.name == slug
        ).first()
        if scenario:
            scenario.probability = prob
            scenario.probability_label = (
                "Polymarket prediction market — crowd-sourced probability, updated daily. "
                "Not an official forecast."
            )
            count += 1

    if count > 0:
        db.commit()
    return count
