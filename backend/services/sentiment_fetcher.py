"""
Sentiment analysis on cached news articles using VADER.
No external API — works on articles already stored in the DB.

Methodology:
  For each article, run VADER compound score and count keyword matches
  per political scenario. Returns raw signal counts for blending into
  probability estimates by probability_engine.py.
"""
from __future__ import annotations
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


def _keyword_score(text: str) -> dict[str, float]:
    """Return raw keyword hit counts per scenario for a piece of text."""
    text_lower = text.lower()
    scores: dict[str, float] = {slug: 0.0 for slug in SCENARIO_KEYWORDS}
    for slug, keywords in SCENARIO_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in text_lower:
                scores[slug] += 1.0
    return scores


def analyze_news(db: Session, max_articles: int = 200) -> dict[str, float]:
    """
    Scan recent cached articles and return a normalised signal dict
    {scenario_slug: relative_weight} summing to 1.0 (or empty if no signal).

    Returns {} if VADER is unavailable or no articles are found.
    """
    articles = (
        db.query(Article)
        .order_by(Article.published_at.desc())
        .limit(max_articles)
        .all()
    )
    if not articles:
        return {}

    totals: dict[str, float] = {slug: 0.0 for slug in SCENARIO_KEYWORDS}

    for article in articles:
        content = f"{article.title or ''} {article.content_snippet or ''}"
        if not content.strip():
            continue

        kw_scores = _keyword_score(content)
        total_hits = sum(kw_scores.values())
        if total_hits == 0:
            continue

        # Optional VADER weighting: boost positive tone for the matched scenario
        if VADER_AVAILABLE:
            vs = _VADER.polarity_scores(content)
            sentiment_weight = 1.0 + _SENTIMENT_BOOST * vs["compound"]
        else:
            sentiment_weight = 1.0

        for slug, hits in kw_scores.items():
            totals[slug] += hits * sentiment_weight

    total = sum(totals.values())
    if total == 0:
        return {}

    return {slug: round(v / total, 6) for slug, v in totals.items()}
