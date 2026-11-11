"""
AI news extraction using Groq (llama-3.1-8b-instant — fast, free tier).
Extracts structured political intelligence from news article text.

API key loaded from .env — never hardcoded.
Data extracted stays local; nothing beyond the article text is sent.
"""
from __future__ import annotations
import json
import os
from dotenv import load_dotenv

load_dotenv()

_MODEL = "llama-3.1-8b-instant"
_MAX_TOKENS = 512

_SYSTEM_PROMPT = """You are a political intelligence analyst specialising in French politics and financial markets.
Given a news article snippet, extract structured data as JSON.
Be concise. Return ONLY valid JSON, no explanation.

Schema:
{
  "political_scenario_signals": {
    "centrist": 0.0,          // 0-1 score: how much this article signals centrist/Macron outcome
    "national_rally": 0.0,    // 0-1 score: RN / Le Pen signal
    "left_wing": 0.0,         // 0-1 score: NFP / Mélenchon signal
    "hung_parliament": 0.0    // 0-1 score: political deadlock signal
  },
  "affected_sectors": [],     // list of CAC40 sectors mentioned (e.g. "Financials", "Energy")
  "key_entities": [],         // political parties, figures, institutions
  "sentiment": "positive|negative|neutral",
  "market_relevance": "high|medium|low",
  "summary_one_line": ""      // max 15 words
}"""


def _get_client():
    key = os.getenv("GROQ_API_KEY")
    if not key:
        raise EnvironmentError("GROQ_API_KEY not set in .env")
    from groq import Groq
    return Groq(api_key=key)


def extract_article(title: str, snippet: str) -> dict | None:
    """
    Extract structured data from a single article.
    Returns parsed dict or None on failure.
    Only the article text is sent to Groq — no user data, no portfolio info.
    """
    content = f"TITLE: {title}\n\nSNIPPET: {snippet[:800]}"
    try:
        client = _get_client()
        response = client.chat.completions.create(
            model=_MODEL,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": content},
            ],
            max_tokens=_MAX_TOKENS,
            temperature=0.1,
        )
        raw = response.choices[0].message.content.strip()
        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw)
    except Exception:
        return None


async def extract_articles_batch(articles: list[dict], max_articles: int = 20) -> list[dict]:
    """
    Run AI extraction on a batch of articles (title + snippet dicts).
    Returns list of {article_id, extraction} dicts.
    Runs synchronously (Groq SDK is blocking); limited to max_articles.
    """
    results = []
    for a in articles[:max_articles]:
        extracted = extract_article(a.get("title", ""), a.get("snippet", ""))
        if extracted:
            results.append({"article_id": a.get("id"), "extraction": extracted})
    return results


def groq_available() -> bool:
    """Check if Groq API key is configured."""
    return bool(os.getenv("GROQ_API_KEY"))
