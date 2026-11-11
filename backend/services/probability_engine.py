"""
Blends signals into probabilities for the four scenario buckets.

Weights:
  - Analyst prior (fixed, PoliticalScenario.prior_probability)          40%
  - Presidential poll simulation (Wikipedia polls → bloc win odds)      35%
  - News signal (Groq extractions; keyword fallback)                    15%
  - Reddit keyword frequency                                             5%
  - Google Trends search volume                                          5%

The prior is never overwritten, so repeated runs cannot compound on their own output.
Missing sources hand their weight to the prior. Only the daily background job
persists results (with an audit row and a daily snapshot); API reads are side-effect free.

The poll simulation covers presidential outcomes only. "Hung parliament" is not a
presidential outcome, so it keeps its prior share inside the poll signal and the
three presidential blocs split the remainder.
"""
from __future__ import annotations
from sqlalchemy.orm import Session
from models import PoliticalScenario

_BASE_WEIGHTS = {
    "polls":  0.35,
    "news":   0.15,
    "reddit": 0.05,
    "trends": 0.05,
}
_PRIOR_WEIGHT = 0.40

_SCENARIO_SLUGS = ["centrist", "national_rally", "left_wing", "hung_parliament"]


def _normalise(d: dict[str, float]) -> dict[str, float]:
    total = sum(d.values())
    if total <= 0:
        return {k: 1.0 / len(d) for k in d}
    return {k: v / total for k, v in d.items()}


def get_prior_from_db(db: Session) -> dict[str, float]:
    rows = db.query(PoliticalScenario).filter(PoliticalScenario.name.in_(_SCENARIO_SLUGS)).all()
    prior = {r.name: float(r.prior_probability if r.prior_probability is not None else r.probability) for r in rows}
    for slug in _SCENARIO_SLUGS:
        prior.setdefault(slug, 1.0 / len(_SCENARIO_SLUGS))
    return _normalise(prior)


def poll_signal_from_presidential(presidential: dict | None, prior: dict[str, float]) -> dict[str, float]:
    if not presidential or not presidential.get("scenario_signal"):
        return {}
    hung = prior.get("hung_parliament", 0.0)
    sig = presidential["scenario_signal"]
    out = {slug: (1 - hung) * float(sig.get(slug, 0.0)) for slug in ("centrist", "national_rally", "left_wing")}
    out["hung_parliament"] = hung
    return out


def write_probabilities_to_db(db: Session, blended: dict[str, float], sources_active: list[str]) -> int:
    from models import ProbabilityRevision
    rows = {r.name: r for r in db.query(PoliticalScenario).all() if r.name in _SCENARIO_SLUGS}
    label = "blended: prior + " + (", ".join(sources_active) if sources_active else "no live sources")
    updated = 0
    for slug, new_prob in blended.items():
        row = rows.get(slug)
        if not row or abs(row.probability - new_prob) < 0.005:
            continue
        db.add(ProbabilityRevision(
            scenario_id=row.id,
            old_probability=row.probability,
            new_probability=new_prob,
            source="blended_signal",
            rationale=label,
        ))
        row.probability = new_prob
        row.probability_label = label
        updated += 1
    if updated:
        db.commit()
    return updated


def blend(prior: dict[str, float], signals: dict[str, dict[str, float]]) -> dict[str, float]:
    available = {k: v for k, v in signals.items() if v and k in _BASE_WEIGHTS}
    prior_weight = _PRIOR_WEIGHT + sum(w for k, w in _BASE_WEIGHTS.items() if k not in available)
    blended = {s: prior_weight * prior.get(s, 0.0) for s in _SCENARIO_SLUGS}
    for source, signal in available.items():
        norm = _normalise({s: float(signal.get(s, 0.0)) for s in _SCENARIO_SLUGS})
        for s in _SCENARIO_SLUGS:
            blended[s] += _BASE_WEIGHTS[source] * norm[s]
    return _normalise(blended)


async def compute_probabilities(db: Session, persist: bool = False) -> dict:
    """Run all sources and blend with the fixed prior. Never raises."""
    from services.sentiment_fetcher import analyze_news
    from services.reddit_fetcher import fetch_reddit_signal
    from services.trends_fetcher import fetch_trends_signal
    from services.store import get_cache, save_snapshot

    prior = get_prior_from_db(db)
    signals: dict[str, dict[str, float]] = {"polls": {}, "news": {}, "reddit": {}, "trends": {}}

    try:
        signals["polls"] = poll_signal_from_presidential(get_cache(db, "presidential"), prior)
    except Exception:
        pass
    try:
        signals["news"] = analyze_news(db)
    except Exception:
        pass
    try:
        signals["reddit"] = await fetch_reddit_signal()
    except Exception:
        pass
    try:
        signals["trends"] = await fetch_trends_signal()
    except Exception:
        pass

    sources_ok = [k for k, v in signals.items() if v]
    blended = blend(prior, signals)

    if persist:
        try:
            write_probabilities_to_db(db, blended, sources_ok)
            save_snapshot(db, "scenarios", {"probabilities": blended, "prior": prior, "sources_active": sources_ok})
        except Exception:
            db.rollback()

    weights = {"prior": _PRIOR_WEIGHT, **_BASE_WEIGHTS}
    return {
        "probabilities": blended,
        "sources": {k: {"available": bool(v), "signal": v, "weight": _BASE_WEIGHTS[k]} for k, v in signals.items()},
        "sources_active": sources_ok,
        "prior": prior,
        "weights": weights,
        "methodology": (
            "40% fixed analyst prior + 35% presidential poll simulation (Wikipedia polls, Monte Carlo) "
            "+ 15% news (Groq article extraction, keyword fallback) + 5% Reddit keywords + 5% Google Trends. "
            "Unavailable sources hand their weight to the prior. The prior is never overwritten by the blend."
        ),
    }
