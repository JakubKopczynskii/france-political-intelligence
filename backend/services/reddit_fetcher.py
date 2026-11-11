"""
Reddit public JSON API — no auth, no API key required.
Fetches top posts from r/france and r/politique (French political subreddits).

Reddit's public JSON endpoint returns up to 100 posts per request.
We set a custom User-Agent to avoid 429s.
"""
from __future__ import annotations
import asyncio
from sqlalchemy.orm import Session
from services.sentiment_fetcher import _keyword_score, SCENARIO_KEYWORDS

_USER_AGENT = "FrancePoliticalIntelligence/0.1 (research; local MVP)"
_SUBREDDITS = ["france", "politique", "european", "europe"]
_MAX_POSTS = 50


async def _fetch_subreddit(subreddit: str, client) -> list[dict]:
    """Fetch hot posts from a subreddit using the public JSON API."""
    url = f"https://www.reddit.com/r/{subreddit}/hot.json"
    params = {"limit": _MAX_POSTS, "raw_json": 1}
    headers = {"User-Agent": _USER_AGENT}
    try:
        resp = await client.get(url, params=params, headers=headers, timeout=10)
        if resp.status_code != 200:
            return []
        data = resp.json()
        posts = data.get("data", {}).get("children", [])
        return [p["data"] for p in posts if p.get("data")]
    except Exception:
        return []


async def fetch_reddit_signal() -> dict[str, float]:
    """
    Pull Reddit posts and return a normalised signal dict
    {scenario_slug: relative_weight} summing to 1.0.
    Returns {} on failure.
    """
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            results = await asyncio.gather(
                *[_fetch_subreddit(sub, client) for sub in _SUBREDDITS],
                return_exceptions=True,
            )
    except Exception:
        return {}

    totals: dict[str, float] = {slug: 0.0 for slug in SCENARIO_KEYWORDS}
    post_count = 0

    for posts in results:
        if isinstance(posts, Exception) or not posts:
            continue
        for post in posts:
            title = post.get("title", "")
            selftext = post.get("selftext", "")
            score = post.get("score", 1)  # upvote count — weight by engagement
            content = f"{title} {selftext}"
            kw = _keyword_score(content)
            total_hits = sum(kw.values())
            if total_hits == 0:
                continue
            weight = max(1, min(score, 500)) / 100  # cap at 5×, floor at 0.01
            for slug, hits in kw.items():
                totals[slug] += hits * weight
            post_count += 1

    total = sum(totals.values())
    if total == 0:
        return {}

    return {slug: round(v / total, 6) for slug, v in totals.items()}
