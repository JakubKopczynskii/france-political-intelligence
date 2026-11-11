"""
AI news extraction using Groq (default model openai/gpt-oss-20b; override with GROQ_MODEL in .env).
Extracts structured political intelligence from news article text.

API key loaded from .env — never hardcoded.
Data extracted stays local; nothing beyond the article text is sent.
"""
from __future__ import annotations
import json
import logging
import os
from dotenv import load_dotenv

load_dotenv()

log = logging.getLogger(__name__)

_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
PROMPT_VERSION = "0.3.0"
_MAX_TOKENS = 1024  # gpt-oss spends part of the budget on reasoning tokens

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
  // Score 0 for scenarios the article says nothing about. Articles may be in French or English.
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
    Returns parsed dict or None on failure (failures are logged).
    Only the article text is sent to Groq — no user data, no portfolio info.
    """
    content = f"TITLE: {title}\n\nSNIPPET: {snippet[:800]}"
    try:
        response = _get_client().chat.completions.create(
            model=_MODEL,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": content},
            ],
            max_tokens=_MAX_TOKENS,
            temperature=0.1,
            response_format={"type": "json_object"},
        )
        raw = (response.choices[0].message.content or "").strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1].removeprefix("json")
        return json.loads(raw)
    except Exception as e:
        log.warning("Groq extraction failed (%s): %s", _MODEL, str(e)[:300])
        print(f"[groq] extraction failed ({_MODEL}): {str(e)[:200]}")
        return None


async def extract_articles_batch(articles: list[dict], max_articles: int = 20) -> list[dict]:
    """Extract a batch without persisting. Each blocking Groq call runs in a worker thread."""
    import asyncio
    results = []
    for a in articles[:max_articles]:
        extracted = await asyncio.to_thread(extract_article, a.get("title", ""), a.get("snippet", ""))
        if extracted:
            results.append({"article_id": a.get("id"), "extraction": extracted})
    return results


async def run_extraction(db, limit: int = 30) -> dict:
    """
    Extract the most recent real articles that have no stored analysis yet and
    save each result as an AIAnalysis row. Returns {"processed", "saved"}.
    """
    import asyncio
    from datetime import datetime, timezone
    from models import AIAnalysis, Article

    done_ids = {r[0] for r in db.query(AIAnalysis.article_id).filter(AIAnalysis.provider == "groq").all()}
    candidates = (
        db.query(Article)
        .filter(Article.is_synthetic == False, Article.is_duplicate == False)
        .order_by(Article.published_at.desc())
        .limit(limit * 4)
        .all()
    )
    todo = [a for a in candidates if a.id not in done_ids][:limit]
    saved = 0
    for a in todo:
        extracted = await asyncio.to_thread(extract_article, a.title or "", a.content_snippet or "")
        if not extracted:
            continue
        db.add(AIAnalysis(
            article_id=a.id,
            provider="groq",
            model_name=_MODEL,
            prompt_version=PROMPT_VERSION,
            information_cutoff=datetime.now(timezone.utc),
            interpretations=json.dumps(extracted),
            raw_response=json.dumps(extracted),
            human_review_required=True,
            is_valid=True,
        ))
        db.commit()
        saved += 1
    return {"processed": len(todo), "saved": saved}


def load_extractions(db, article_ids: list[int]) -> dict[int, dict]:
    from models import AIAnalysis
    if not article_ids:
        return {}
    rows = (
        db.query(AIAnalysis)
        .filter(AIAnalysis.article_id.in_(article_ids), AIAnalysis.provider == "groq", AIAnalysis.is_valid == True)
        .order_by(AIAnalysis.id)
        .all()
    )
    out = {}
    for r in rows:
        try:
            out[r.article_id] = json.loads(r.interpretations)
        except (TypeError, ValueError):
            continue
    return out


def groq_available() -> bool:
    """Check if Groq API key is configured."""
    return bool(os.getenv("GROQ_API_KEY"))
