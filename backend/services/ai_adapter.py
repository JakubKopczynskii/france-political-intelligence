"""
Provider-neutral AI adapter with deterministic fallback.
When AI_PROVIDER=none (default), uses deterministic keyword extraction.
Never fabricates facts or financial figures.
"""
import json
import os
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from services.rss_ingestion import apply_topic_tags


class AIProvider(str, Enum):
    NONE = "none"
    GEMINI = "gemini"
    GROQ = "groq"
    OPENROUTER = "openrouter"


def get_active_provider() -> AIProvider:
    """Read AI_PROVIDER from env. Default: none (deterministic)."""
    val = os.environ.get("AI_PROVIDER", "none").lower().strip()
    try:
        return AIProvider(val)
    except ValueError:
        return AIProvider.NONE


_CATEGORY_KEYWORDS = {
    "fiscal": ["budget", "déficit", "impôt", "taxe", "dette", "tax", "deficit", "spending"],
    "election": ["election", "élection", "vote", "parlement", "parliament", "majorité"],
    "ecb": ["bce", "ecb", "lagarde", "taux directeur", "monetary", "rate"],
    "energy": ["énergie", "pétrole", "gaz", "nucléaire", "energy", "oil", "gas"],
    "trade": ["commerce", "exportation", "tarifaire", "trade", "tariff"],
    "defence": ["défense", "otan", "nato", "armée", "military"],
    "macro": ["croissance", "récession", "pib", "gdp", "chômage", "inflation", "growth"],
    "companies": ["résultats", "bénéfice", "earnings", "profit", "dividende"],
}

_HORIZON_KEYWORDS = {
    "immediate": ["aujourd'hui", "today", "urgent", "immédiat", "breaking"],
    "short_term": ["semaine", "mois", "week", "month", "prochain", "next"],
    "long_term": ["2025", "2026", "2027", "2028", "année prochaine", "next year", "long term"],
}


def _infer_category(title: str, content: str) -> str:
    text = f"{title} {content}".lower()
    for cat, keywords in _CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw in text:
                return cat
    return "general"


def _infer_horizon(title: str, content: str) -> str:
    text = f"{title} {content}".lower()
    for horizon, keywords in _HORIZON_KEYWORDS.items():
        for kw in keywords:
            if kw in text:
                return horizon
    return "medium_term"


def deterministic_extract(article: dict) -> dict:
    """
    Fallback extraction using keyword matching.
    Returns the same structure as extract_news_event.
    Does NOT use AI.
    """
    title = article.get("title", "")
    content = article.get("content_snippet", "")

    topic_tags = apply_topic_tags(title, content)
    category = _infer_category(title, content)
    horizon = _infer_horizon(title, content)

    # Infer affected sectors from topic tags
    sector_map = {
        "fiscal": ["Financials", "Utilities"],
        "ecb": ["Financials", "Real Estate", "Utilities"],
        "energy": ["Energy", "Industrials"],
        "trade": ["Industrials", "Consumer Staples"],
        "defence": ["Industrials"],
        "macro": ["Financials", "Consumer Discretionary"],
        "companies": [],
        "election": ["Financials", "Energy"],
    }
    affected_sectors = []
    for tag in topic_tags:
        for s in sector_map.get(tag, []):
            if s not in affected_sectors:
                affected_sectors.append(s)

    return {
        "headline": title,
        "event_category": category,
        "political_actors": [],
        "policy_tags": topic_tags,
        "affected_sectors": affected_sectors,
        "affected_companies": article.get("affected_companies", []),
        "time_horizon": horizon,
        "uncertainties": "Deterministic extraction — no AI analysis available. Manual review recommended.",
        "information_type": "reported_claim",
        "confidence": 0.3,
        "provider": "none",
        "model": "deterministic_keyword_extractor_v0.1",
        "is_ai_generated": False,
        "prompt_version": "N/A",
        "disclaimer": "This extraction used keyword matching only. No AI was used. Human review required for investment decisions.",
    }


async def extract_news_event(article: dict, provider: Optional[AIProvider] = None) -> dict:
    """
    Extract structured event information from a news article.
    Falls back to deterministic extraction if no AI provider configured.

    Returns structured extraction dict. Never invents financial figures.
    """
    if provider is None:
        provider = get_active_provider()

    if provider == AIProvider.NONE:
        return deterministic_extract(article)

    # Provider integrations — only implement when API key is present
    api_key_map = {
        AIProvider.GEMINI: "GEMINI_API_KEY",
        AIProvider.GROQ: "GROQ_API_KEY",
        AIProvider.OPENROUTER: "OPENROUTER_API_KEY",
    }
    env_key = api_key_map.get(provider)
    if not env_key or not os.environ.get(env_key):
        return {
            **deterministic_extract(article),
            "disclaimer": f"AI provider '{provider}' requested but API key not configured. Fell back to deterministic extraction.",
        }

    # Provider-specific implementations would go here.
    # For MVP: fall back to deterministic with a warning.
    # Production: implement structured output calls per provider SDK.
    return {
        **deterministic_extract(article),
        "disclaimer": f"AI provider '{provider}' integration not yet implemented in MVP. Using deterministic fallback.",
    }
