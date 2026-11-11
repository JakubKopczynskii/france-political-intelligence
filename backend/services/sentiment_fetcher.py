"""
Sentiment analysis on cached news articles using VADER.
No external API — works on articles already stored in the DB.

Methodology:
  For each article, run VADER compound score and count keyword matches
  per political scenario. Returns raw signal counts for blending into
  probability estimates by probability_engine.py.
"""
from __future__ import annotations
import re
from sqlalchemy.orm import Session
from models import Article

try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    _VADER = SentimentIntensityAnalyzer()
    VADER_AVAILABLE = True
except ImportError:
    VADER_AVAILABLE = False

# Keywords that signal each scenario — French and English
SCENARIO_KEYWORDS: dict[str, list[str]] = {
    "national_rally": [
        "Marine Le Pen", "Le Pen", "Rassemblement National", "RN",
        "Jordan Bardella", "extrême droite", "Bardella",
        "front national", "national rally",
    ],
    "left_wing": [
        "Mélenchon", "NUPES", "NFP", "Nouveau Front Populaire", "LFI",
        "La France Insoumise", "union de la gauche", "gauche",
        "left wing", "left-wing coalition",
    ],
    "centrist": [
        "Macron", "Renaissance", "LREM", "centre", "centriste",
        "Bayrou", "MoDem", "Horizons", "centre droit",
        "macroniste", "macronism",
    ],
    "hung_parliament": [
        "blocage", "impasse", "cohabitation", "majorité introuvable",
        "crise politique", "dissolution", "motion de censure",
        "hung parliament", "deadlock", "instabilité politique",
        "no majority", "sans majorité",
    ],
}

# Sentiment modifier: positive article about a scenario boosts it slightly more
_SENTIMENT_BOOST = 0.3


_KEYWORD_PATTERNS = {
    slug: [re.compile(r"(?<!\w)" + re.escape(kw) + r"(?!\w)", 0 if kw.isupper() else re.IGNORECASE) for kw in kws]
    for slug, kws in SCENARIO_KEYWORDS.items()
}


def _keyword_score(text: str) -> dict[str, float]:
    """Whole-word keyword hits per scenario. All-caps acronyms (RN, LFI) match case-sensitively."""
    return {slug: float(sum(1 for p in pats if p.search(text))) for slug, pats in _KEYWORD_PATTERNS.items()}


_RELEVANCE_WEIGHT = {"high": 1.0, "medium": 0.6, "low": 0.3}


def analyze_news(db: Session, max_articles: int = 200) -> dict[str, float]:
    """
    Scan recent cached articles and return a normalised signal dict
    {scenario_slug: relative_weight} summing to 1.0 (or empty if no signal).

    Per article:
      - If a stored Groq extraction exists, use its scenario signals weighted by
        market relevance (works for French and English text).
      - Otherwise count scenario keywords. VADER tone weighting is applied only to
        English articles, because VADER's lexicon is English-only.
    """
    from services.groq_extractor import load_extractions

    articles = (
        db.query(Article)
        .filter(Article.is_duplicate == False)
        .order_by(Article.published_at.desc())
        .limit(max_articles)
        .all()
    )
    if not articles:
        return {}

    extractions = load_extractions(db, [a.id for a in articles])
    totals: dict[str, float] = {slug: 0.0 for slug in SCENARIO_KEYWORDS}

    for article in articles:
        ai = extractions.get(article.id)
        signals = (ai or {}).get("political_scenario_signals") if isinstance(ai, dict) else None
        if isinstance(signals, dict):
            weight = _RELEVANCE_WEIGHT.get(str(ai.get("market_relevance", "low")).lower(), 0.3)
            for slug in totals:
                try:
                    totals[slug] += weight * max(0.0, min(1.0, float(signals.get(slug, 0.0))))
                except (TypeError, ValueError):
                    pass
            continue

        content = f"{article.title or ''} {article.content_snippet or ''}"
        if not content.strip():
            continue
        kw_scores = _keyword_score(content)
        if sum(kw_scores.values()) == 0:
            continue
        sentiment_weight = 1.0
        if VADER_AVAILABLE and (article.language or "").lower().startswith("en"):
            sentiment_weight = 1.0 + _SENTIMENT_BOOST * _VADER.polarity_scores(content)["compound"]
        for slug, hits in kw_scores.items():
            totals[slug] += hits * sentiment_weight

    total = sum(totals.values())
    if total == 0:
        return {}
    return {slug: round(v / total, 6) for slug, v in totals.items()}
