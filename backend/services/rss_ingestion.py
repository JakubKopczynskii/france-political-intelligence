"""
RSS ingestion service — fetch, normalize, deduplicate, tag.
"""
import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Optional

import aiohttp
import feedparser


def compute_fingerprint(url: str, title: str) -> str:
    """SHA256 of normalized url+title."""
    normalized = f"{url.strip().lower()}{title.strip().lower()}"
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


_TOPIC_KEYWORDS = {
    "politics": [
        "election", "parlement", "président", "ministre", "parti", "vote",
        "assemblée", "sénat", "premier ministre", "politique", "gouvernement",
        "president", "parliament", "minister", "party", "government", "political",
        "coalition", "majorité", "majority", "élection",
    ],
    "fiscal": [
        "budget", "impôt", "taxe", "déficit", "dette", "fiscal",
        "dépenses", "recettes", "pib", "gdp", "tax", "deficit", "spending",
        "dette publique", "public debt", "austerity", "austérité",
        "financement", "emprunt", "oat", "obligat",
    ],
    "ecb": [
        "bce", "ecb", "lagarde", "taux directeur", "inflation", "banque centrale",
        "monetary policy", "politique monétaire", "interest rate", "taux d'intérêt",
        "quantitative", "qe", "deposit facility", "governing council",
    ],
    "energy": [
        "énergie", "pétrole", "gaz", "nucléaire", "renouvelable", "électricité",
        "energy", "oil", "gas", "nuclear", "renewable", "electricity",
        "brent", "wti", "lng", "gnl", "carburant", "fuel",
    ],
    "defence": [
        "défense", "armée", "militaire", "otan", "nato", "armement", "guerre",
        "defence", "defense", "military", "army", "war", "weapon", "ukraine",
        "sécurité nationale", "national security",
    ],
    "trade": [
        "commerce", "exportation", "importation", "tarifaire", "douane",
        "trade", "export", "import", "tariff", "customs", "protectionism",
        "protectionnisme", "wto", "omc",
    ],
    "macro": [
        "croissance", "récession", "pib", "gdp", "chômage", "unemployment",
        "inflation", "growth", "recession", "recovery", "reprise",
        "consommation", "consumption", "investissement", "investment",
        "productivité", "productivity",
    ],
    "companies": [
        "résultats", "bénéfice", "profit", "action", "bourse", "cac",
        "results", "earnings", "revenue", "stock", "market cap",
        "dividende", "dividend", "acquisition", "merger", "fusion",
    ],
}


TOPIC_WEIGHTS = {
    "politics": 1.0,
    "fiscal": 0.9,
    "ecb": 0.85,
    "defence": 0.8,
    "energy": 0.7,
    "trade": 0.65,
    "macro": 0.6,
    "companies": 0.5,
}


def compute_relevance_score(tags: list) -> float:
    if not tags:
        return 0.1
    return min(1.0, max(TOPIC_WEIGHTS.get(t, 0.3) for t in tags))


def apply_topic_tags(title: str, content: str) -> list:
    """
    Deterministic keyword-based tagging.
    Returns list of matching topic tags.
    """
    text = f"{title} {content}".lower()
    tags = []
    for tag, keywords in _TOPIC_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in text:
                tags.append(tag)
                break
    return tags


def normalize_entry(entry: dict, source_name: str) -> dict:
    """Normalize a feedparser entry to standard fields."""
    title = entry.get("title", "").strip()
    url = entry.get("link", entry.get("url", "")).strip()

    # Try to get content
    raw_summary = entry.get("summary", "")
    content = ""
    if raw_summary:
        content = raw_summary
    elif "content" in entry and entry["content"]:
        content = entry["content"][0].get("value", "")

    # Extract image URL before stripping HTML
    image_url = None
    media_thumbnails = entry.get("media_thumbnail", [])
    if media_thumbnails:
        image_url = media_thumbnails[0].get("url")
    if not image_url:
        media_content = entry.get("media_content", [])
        for mc in media_content:
            if mc.get("type", "").startswith("image/") or not mc.get("type"):
                image_url = mc.get("url")
                break
    if not image_url:
        for enc in entry.get("enclosures", []):
            if enc.get("type", "").startswith("image/"):
                image_url = enc.get("href")
                break
    if not image_url:
        m = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', content)
        if m:
            image_url = m.group(1)

    # Strip basic HTML
    content = re.sub(r"<[^>]+>", " ", content).strip()
    content = content[:1000]  # limit snippet

    # Parse published date
    published_at = None
    if "published_parsed" in entry and entry["published_parsed"]:
        try:
            import calendar
            ts = calendar.timegm(entry["published_parsed"])
            published_at = datetime.fromtimestamp(ts, tz=timezone.utc)
        except Exception:
            pass
    if published_at is None and "updated_parsed" in entry and entry["updated_parsed"]:
        try:
            import calendar
            ts = calendar.timegm(entry["updated_parsed"])
            published_at = datetime.fromtimestamp(ts, tz=timezone.utc)
        except Exception:
            pass

    tags = apply_topic_tags(title, content)

    return {
        "title": title,
        "url": url,
        "content_snippet": content,
        "published_at": published_at,
        "language": "fr",  # default; could be detected
        "topic_tags": json.dumps(tags),
        "entities": json.dumps([]),
        "policy_tags": json.dumps([]),
        "affected_sectors": json.dumps([]),
        "affected_companies": json.dumps([]),
        "image_url": image_url,
        "relevance_score": compute_relevance_score(tags),
        "source_name": source_name,
    }


async def fetch_feed(feed_url: str, timeout: int = 30) -> dict:
    """
    Fetch and parse an RSS/Atom feed.
    Returns {success, entries, error, fetched_at}.
    """
    fetched_at = datetime.now(timezone.utc)

    try:
        async with aiohttp.ClientSession() as session:
            headers = {"User-Agent": "FranceIntelMVP/0.1 (research; +https://localhost:3000)"}
            async with session.get(feed_url, timeout=aiohttp.ClientTimeout(total=timeout), headers=headers) as resp:
                if resp.status != 200:
                    return {
                        "success": False,
                        "entries": [],
                        "error": f"HTTP {resp.status}",
                        "fetched_at": fetched_at,
                    }
                content = await resp.read()
    except aiohttp.ClientError as e:
        return {"success": False, "entries": [], "error": str(e), "fetched_at": fetched_at}
    except Exception as e:
        return {"success": False, "entries": [], "error": str(e), "fetched_at": fetched_at}

    try:
        parsed = feedparser.parse(content)
    except Exception as e:
        return {"success": False, "entries": [], "error": f"Parse error: {e}", "fetched_at": fetched_at}

    entries = []
    for entry in parsed.entries:
        try:
            normalized = normalize_entry(dict(entry), feed_url)
            if normalized["url"] and normalized["title"]:
                normalized["fingerprint"] = compute_fingerprint(normalized["url"], normalized["title"])
                entries.append(normalized)
        except Exception:
            continue

    return {
        "success": True,
        "entries": entries,
        "error": None,
        "fetched_at": fetched_at,
    }


def detect_duplicates_in_batch(articles: list) -> list:
    """
    Mark duplicates within a batch using fingerprint exact match.
    First occurrence wins; subsequent occurrences marked as duplicate.
    Returns the articles list with 'is_duplicate' field set.
    """
    seen_fingerprints: set = set()
    result = []
    for article in articles:
        fp = article.get("fingerprint", "")
        if fp in seen_fingerprints:
            article = dict(article)
            article["is_duplicate"] = True
        else:
            seen_fingerprints.add(fp)
            article = dict(article)
            article["is_duplicate"] = False
        result.append(article)
    return result
