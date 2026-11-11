import asyncio
import json
import yaml
import os
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import or_
from database import get_db
from models import Article, Event, Feed, Source
from services.rss_ingestion import fetch_feed, compute_fingerprint, apply_topic_tags
import json as _json

router = APIRouter()


def _importance_label(score: float | None) -> str:
    if score is None:
        return "LOW"
    if score >= 0.9:
        return "HIGH"
    if score >= 0.6:
        return "MEDIUM"
    return "LOW"


def _serialize_article(a: Article, source_name: str = "Unknown") -> dict:
    score = a.relevance_score or 0.0
    return {
        "id": a.id,
        "title": a.title,
        "url": a.url,
        "content_snippet": a.content_snippet,
        "published_at": a.published_at.isoformat() if a.published_at else None,
        "retrieved_at": a.retrieved_at.isoformat() if a.retrieved_at else None,
        "language": a.language,
        "topic_tags": _json.loads(a.topic_tags or "[]"),
        "entities": _json.loads(a.entities or "[]"),
        "policy_tags": _json.loads(a.policy_tags or "[]"),
        "affected_sectors": _json.loads(a.affected_sectors or "[]"),
        "affected_companies": _json.loads(a.affected_companies or "[]"),
        "relevance_score": score,
        "importance_label": _importance_label(score),
        "image_url": getattr(a, "image_url", None),
        "source_quality": a.source_quality,
        "source_name": source_name,
        "information_type": "reported_claim",
        "is_duplicate": a.is_duplicate,
        "event_id": a.event_id,
        "is_synthetic": a.is_synthetic,
    }


def _serialize_event(e: Event) -> dict:
    return {
        "id": e.id,
        "headline": e.headline,
        "description": e.description,
        "event_category": e.event_category,
        "political_actors": _json.loads(e.political_actors or "[]"),
        "policy_tags": _json.loads(e.policy_tags or "[]"),
        "affected_sectors": _json.loads(e.affected_sectors or "[]"),
        "affected_companies": _json.loads(e.affected_companies or "[]"),
        "verification_status": e.verification_status,
        "information_type": e.information_type,
        "source_name": "Synthetic Demo",
        "source_article_ids": _json.loads(e.source_article_ids or "[]"),
        "novelty_score": e.novelty_score,
        "time_horizon": e.time_horizon,
        "uncertainties": e.uncertainties,
        "is_synthetic": e.is_synthetic,
        "published_at": e.created_at.isoformat() if e.created_at else None,
        "created_at": e.created_at.isoformat() if e.created_at else None,
    }


@router.get("/api/news")
def list_articles(
    topic: str = Query(None, description="Filter by topic tag"),
    search: str = Query(None, description="Search in title"),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    q = db.query(Article).filter(Article.is_duplicate == False)
    if topic:
        q = q.filter(Article.topic_tags.contains(topic))
    if search:
        q = q.filter(Article.title.ilike(f"%{search}%"))
    total = q.count()
    articles = q.order_by(Article.relevance_score.desc(), Article.published_at.desc()).offset(offset).limit(limit).all()
    # Build feed_id → source_name lookup
    feed_ids = list({a.feed_id for a in articles if a.feed_id})
    feeds = {f.id: f for f in db.query(Feed).filter(Feed.id.in_(feed_ids)).all()} if feed_ids else {}
    source_ids = list({f.source_id for f in feeds.values() if f.source_id})
    sources = {s.id: s for s in db.query(Source).filter(Source.id.in_(source_ids)).all()} if source_ids else {}
    def _source_name(a: Article) -> str:
        feed = feeds.get(a.feed_id)
        if not feed:
            return "Unknown"
        src = sources.get(feed.source_id)
        return src.name if src else "Unknown"
    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "articles": [_serialize_article(a, source_name=_source_name(a)) for a in articles],
    }


@router.get("/api/news/{article_id}")
def get_article(article_id: int, db: Session = Depends(get_db)):
    a = db.query(Article).filter(Article.id == article_id).first()
    if not a:
        raise HTTPException(status_code=404, detail="Article not found")
    source_name = "Unknown"
    if a.feed_id:
        feed = db.query(Feed).filter(Feed.id == a.feed_id).first()
        if feed and feed.source_id:
            src = db.query(Source).filter(Source.id == feed.source_id).first()
            if src:
                source_name = src.name
    return _serialize_article(a, source_name=source_name)


@router.get("/api/events")
def list_events(
    category: str = Query(None),
    search: str = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    q = db.query(Event)
    if category:
        q = q.filter(Event.event_category == category)
    if search:
        q = q.filter(Event.headline.ilike(f"%{search}%"))
    total = q.count()
    events = q.order_by(Event.created_at.desc()).offset(offset).limit(limit).all()
    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "events": [_serialize_event(e) for e in events],
    }


@router.get("/api/events/{event_id}")
def get_event(event_id: int, db: Session = Depends(get_db)):
    e = db.query(Event).filter(Event.id == event_id).first()
    if not e:
        raise HTTPException(status_code=404, detail="Event not found")
    return _serialize_event(e)


@router.get("/api/feeds")
def list_feeds(db: Session = Depends(get_db)):
    feeds = db.query(Feed).all()
    result = []
    for f in feeds:
        source = db.query(Source).filter(Source.id == f.source_id).first()
        result.append({
            "id": f.id,
            "source_name": source.name if source else "Unknown",
            "feed_url": f.feed_url,
            "topic_tags": _json.loads(f.topic_tags or "[]"),
            "health_status": f.health_status,
            "last_fetched_at": f.last_fetched_at.isoformat() if f.last_fetched_at else None,
            "last_success_at": f.last_success_at.isoformat() if f.last_success_at else None,
            "article_count": f.article_count,
        })
    return result


async def _refresh_single_feed(feed_id: int):
    """Background task to fetch a single feed and store new articles."""
    from database import SessionLocal
    db = SessionLocal()
    try:
        feed = db.query(Feed).filter(Feed.id == feed_id).first()
        if not feed:
            return
        source = db.query(Source).filter(Source.id == feed.source_id).first()
        source_name = source.name if source else "Unknown"

        result = await fetch_feed(feed.feed_url)
        feed.last_fetched_at = result["fetched_at"]

        if result["success"]:
            feed.health_status = "ok"
            feed.last_success_at = result["fetched_at"]
            new_count = 0
            for entry in result["entries"]:
                fp = entry.get("fingerprint") or compute_fingerprint(entry.get("url", ""), entry.get("title", ""))
                existing = db.query(Article).filter(Article.fingerprint == fp).first()
                if not existing:
                    article = Article(
                        feed_id=feed.id,
                        title=entry.get("title", ""),
                        url=entry.get("url", ""),
                        content_snippet=entry.get("content_snippet", ""),
                        published_at=entry.get("published_at"),
                        retrieved_at=result["fetched_at"],
                        language=entry.get("language", "fr"),
                        fingerprint=fp,
                        topic_tags=entry.get("topic_tags", "[]"),
                        entities=entry.get("entities", "[]"),
                        policy_tags=entry.get("policy_tags", "[]"),
                        affected_sectors=entry.get("affected_sectors", "[]"),
                        affected_companies=entry.get("affected_companies", "[]"),
                        image_url=entry.get("image_url"),
                        relevance_score=entry.get("relevance_score", 0.5),
                        source_quality=source.quality_tier if source else 3,
                        is_synthetic=False,
                    )
                    db.add(article)
                    new_count += 1
            feed.article_count = (feed.article_count or 0) + new_count
        else:
            feed.health_status = "error"
        db.commit()
    except Exception as e:
        db.rollback()
    finally:
        db.close()


@router.post("/api/news/refresh")
async def refresh_news(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    feeds = db.query(Feed).filter(Feed.health_status != "disabled").all()
    for feed in feeds:
        background_tasks.add_task(_refresh_single_feed, feed.id)
    return {
        "message": f"Refresh started for {len(feeds)} feeds",
        "feed_ids": [f.id for f in feeds],
        "note": "Results will appear after background fetch completes. Check /api/health/feeds for status.",
    }


@router.post("/api/feeds/refresh")
async def refresh_feeds(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    return await refresh_news(background_tasks, db)
