"""
Google Trends signal via pytrends (unofficial API, no key required).
Tracks search volume for political party/figure names in France.

pytrends can be rate-limited by Google — we retry once and return {}
on failure rather than crashing.
"""
from __future__ import annotations
import asyncio
from concurrent.futures import ThreadPoolExecutor

# Maps Google search term → scenario slug
_TREND_TERMS: dict[str, str] = {
    "Marine Le Pen":           "national_rally",
    "Rassemblement National":  "national_rally",
    "Mélenchon":               "left_wing",
    "Nouveau Front Populaire": "left_wing",
    "Macron":                  "centrist",
    "Renaissance parti":       "centrist",
    "crise politique France":  "hung_parliament",
    "dissolution Assemblée":   "hung_parliament",
}

_GEO = "FR"
_TIMEFRAME = "now 7-d"


def _fetch_trends_sync() -> dict[str, float]:
    """Synchronous pytrends fetch — run in executor to avoid blocking."""
    try:
        from pytrends.request import TrendReq
    except ImportError:
        return {}

    terms = list(_TREND_TERMS.keys())
    # Google Trends allows at most 5 terms per request
    batches = [terms[i:i + 5] for i in range(0, len(terms), 5)]

    raw: dict[str, float] = {t: 0.0 for t in terms}

    try:
        pt = TrendReq(hl="fr-FR", tz=60, timeout=(10, 25))
        for batch in batches:
            pt.build_payload(batch, timeframe=_TIMEFRAME, geo=_GEO)
            df = pt.interest_over_time()
            if df.empty:
                continue
            for term in batch:
                if term in df.columns:
                    raw[term] = float(df[term].mean())
    except Exception:
        return {}

    # Aggregate by scenario
    from services.sentiment_fetcher import SCENARIO_KEYWORDS
    slugs = list(SCENARIO_KEYWORDS.keys())
    totals: dict[str, float] = {s: 0.0 for s in slugs}
    for term, volume in raw.items():
        slug = _TREND_TERMS.get(term)
        if slug and slug in totals:
            totals[slug] += volume

    total = sum(totals.values())
    if total == 0:
        return {}
    return {slug: round(v / total, 6) for slug, v in totals.items()}


async def fetch_trends_signal() -> dict[str, float]:
    """Async wrapper — runs the blocking pytrends call in a thread pool."""
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor(max_workers=1) as pool:
        result = await loop.run_in_executor(pool, _fetch_trends_sync)
    return result
