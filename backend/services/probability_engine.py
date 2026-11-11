"""
Blends multiple sentiment signals into final scenario probabilities.

Sources and weights:
  - Analyst prior (seed DB values)         45%
  - Wikipedia election polls               15%
  - RSS news sentiment (VADER + keywords)  20%
  - Reddit signal (r/france, r/politique)   10%
  - Google Trends                           10%
  - Polymarket (when available)            overrides all — treated as market consensus

If a source returns {} (unavailable/no signal), its weight is redistributed
proportionally across the remaining sources.

Calibration rationale:
  Wikipedia election polls are added as a 15% signal — more authoritative than
  social media sentiment but kept below the analyst prior which incorporates
  structural scenario knowledge. Polymarket override reflects the academic finding
  that prediction markets outperform polls and media sentiment for election forecasting
  (Wolfers & Zitzewitz, 2004; Tetlock superforecasters).
"""
from __future__ import annotations
from sqlalchemy.orm import Session
from models import PoliticalScenario

_BASE_WEIGHTS = {
    "wiki_polls": 0.15,
    "news":       0.20,
    "reddit":     0.10,
    "trends":     0.10,
}
_PRIOR_WEIGHT = 0.45

_SCENARIO_SLUGS = ["centrist", "national_rally", "left_wing", "hung_parliament"]


def _normalise(d: dict[str, float]) -> dict[str, float]:
    total = sum(d.values())
    if total <= 0:
        n = len(d)
        return {k: 1.0 / n for k in d}
    return {k: v / total for k, v in d.items()}


def get_prior_from_db(db: Session) -> dict[str, float]:
    """Read current scenario probabilities from DB as the analyst prior."""
    rows = db.query(PoliticalScenario).all()
    prior = {r.name: float(r.probability) for r in rows if r.name in _SCENARIO_SLUGS}
    for slug in _SCENARIO_SLUGS:
        if slug not in prior:
            prior[slug] = 1.0 / len(_SCENARIO_SLUGS)
    return _normalise(prior)


def write_probabilities_to_db(db: Session, blended: dict[str, float], sources_active: list[str]) -> int:
    """
    Write blended probabilities back to PoliticalScenario rows.
    Logs each change as a ProbabilityRevision. Returns count updated.
    Only writes if the blended values differ from current by > 0.5%.
    """
    from models import ProbabilityRevision
    rows = {r.name: r for r in db.query(PoliticalScenario).all() if r.name in _SCENARIO_SLUGS}
    if not rows:
        return 0

    label = "blended: " + (", ".join(sources_active) if sources_active else "prior only")
    updated = 0
    for slug, new_prob in blended.items():
        row = rows.get(slug)
        if not row:
            continue
        if abs(row.probability - new_prob) < 0.005:
            continue
        revision = ProbabilityRevision(
            scenario_id=row.id,
            old_probability=row.probability,
            new_probability=new_prob,
            source="blended_signal",
            rationale=label,
        )
        db.add(revision)
        row.probability = new_prob
        row.probability_label = label
        updated += 1

    if updated:
        db.commit()
    return updated


def blend_signals(
    prior: dict[str, float],
    news: dict[str, float],
    reddit: dict[str, float],
    trends: dict[str, float],
    wiki_polls: dict[str, float] | None = None,
    polymarket: dict[str, float] | None = None,
) -> dict[str, float]:
    # Keep original signature working (overload handles old callers)
    return _blend(prior, news, reddit, trends, wiki_polls or {}, polymarket)


def _blend(
    prior: dict[str, float],
    news: dict[str, float],
    reddit: dict[str, float],
    trends: dict[str, float],
    wiki_polls: dict[str, float],
    polymarket: dict[str, float] | None,
) -> dict[str, float]:
    if polymarket and len(polymarket) >= len(_SCENARIO_SLUGS):
        pm_norm = _normalise({s: polymarket.get(s, 0.0) for s in _SCENARIO_SLUGS})
        if all(v > 0 for v in pm_norm.values()):
            return pm_norm

    signals = {"wiki_polls": wiki_polls, "news": news, "reddit": reddit, "trends": trends}
    available = {k: v for k, v in signals.items() if v}

    missing_weight = sum(_BASE_WEIGHTS[k] for k in _BASE_WEIGHTS if k not in available)
    effective_prior_weight = _PRIOR_WEIGHT + missing_weight

    blended = {s: 0.0 for s in _SCENARIO_SLUGS}
    for slug in _SCENARIO_SLUGS:
        blended[slug] += effective_prior_weight * prior.get(slug, 0.0)

    for source, signal in available.items():
        w = _BASE_WEIGHTS[source]
        for slug in _SCENARIO_SLUGS:
            blended[slug] += w * signal.get(slug, 0.0)

    return _normalise(blended)


async def compute_probabilities(db: Session) -> dict:
    """
    Run all sentiment sources, blend with DB prior, return full result dict.
    Never raises — returns prior on any failure.
    """
    from services.sentiment_fetcher import analyze_news
    from services.reddit_fetcher import fetch_reddit_signal
    from services.trends_fetcher import fetch_trends_signal
    from services.poll_fetcher import fetch_wiki_poll_signal

    prior = get_prior_from_db(db)

    news_signal: dict[str, float] = {}
    reddit_signal: dict[str, float] = {}
    trends_signal: dict[str, float] = {}
    wiki_signal: dict[str, float] = {}
    sources_ok: list[str] = []

    try:
        news_signal = analyze_news(db)
        if news_signal:
            sources_ok.append("news")
    except Exception:
        pass

    try:
        reddit_signal = await fetch_reddit_signal()
        if reddit_signal:
            sources_ok.append("reddit")
    except Exception:
        pass

    try:
        trends_signal = await fetch_trends_signal()
        if trends_signal:
            sources_ok.append("trends")
    except Exception:
        pass

    try:
        wiki_signal = await fetch_wiki_poll_signal()
        if wiki_signal:
            sources_ok.append("wiki_polls")
    except Exception:
        pass

    blended = _blend(
        prior=prior,
        news=news_signal,
        reddit=reddit_signal,
        trends=trends_signal,
        wiki_polls=wiki_signal,
        polymarket=None,
    )

    # Write blended probabilities back to DB so scenario cards show live values
    try:
        write_probabilities_to_db(db, blended, sources_ok)
    except Exception:
        pass

    return {
        "probabilities": blended,
        "sources": {
            "wiki_polls": {"available": bool(wiki_signal),   "signal": wiki_signal},
            "news":       {"available": bool(news_signal),   "signal": news_signal},
            "reddit":     {"available": bool(reddit_signal), "signal": reddit_signal},
            "trends":     {"available": bool(trends_signal), "signal": trends_signal},
        },
        "sources_active": sources_ok,
        "prior": prior,
        "methodology": (
            "Bayesian blend: 45% analyst prior + 15% Wikipedia election polls "
            "+ 20% RSS news VADER sentiment "
            "+ 10% Reddit r/france keyword frequency + 10% Google Trends search volume. "
            "Keyword matching maps party names and political terms to scenario slugs. "
            "VADER compound score weights news articles by sentiment polarity. "
            "Sources absent at fetch time have their weight redistributed to the prior. "
            "Polymarket prediction markets override all signals when available."
        ),
    }
