from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from database import get_db
from models import Article, Event, Feed

router = APIRouter()


@router.get("/api/health")
def health_check(db: Session = Depends(get_db)):
    db_ok = False
    article_count = 0
    event_count = 0
    last_refresh = None
    try:
        db.execute(text("SELECT 1"))
        db_ok = True
        article_count = db.query(Article).count()
        event_count = db.query(Event).count()
        latest_feed = db.query(Feed).filter(Feed.last_fetched_at.isnot(None)).order_by(Feed.last_fetched_at.desc()).first()
        if latest_feed and latest_feed.last_fetched_at:
            last_refresh = latest_feed.last_fetched_at.isoformat()
    except Exception:
        pass
    return {
        "status": "ok",
        "version": "0.1.0",
        "db_ok": db_ok,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "mode": "demo",
        "demo_mode": True,
        "article_count": article_count,
        "event_count": event_count,
        "last_refresh": last_refresh,
    }


@router.get("/api/health/feeds")
def feed_health(db: Session = Depends(get_db)):
    feeds = db.query(Feed).all()
    return [
        {
            "id": f.id,
            "feed_url": f.feed_url,
            "health_status": f.health_status,
            "last_fetched_at": f.last_fetched_at.isoformat() if f.last_fetched_at else None,
            "last_success_at": f.last_success_at.isoformat() if f.last_success_at else None,
            "article_count": f.article_count,
        }
        for f in feeds
    ]
