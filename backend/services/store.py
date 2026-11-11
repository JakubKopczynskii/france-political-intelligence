"""JSON cache and daily snapshot helpers backed by SQLite."""
from __future__ import annotations
import json
from datetime import date, datetime, timedelta, timezone
from sqlalchemy.orm import Session
from models import DataCache, ProbabilitySnapshot


def get_cache(db: Session, key: str, max_age_hours: float | None = None) -> dict | None:
    row = db.query(DataCache).filter(DataCache.key == key).first()
    if not row:
        return None
    if max_age_hours is not None:
        fetched = row.fetched_at if row.fetched_at.tzinfo else row.fetched_at.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) - fetched > timedelta(hours=max_age_hours):
            return None
    return json.loads(row.payload)


def set_cache(db: Session, key: str, payload: dict) -> None:
    row = db.query(DataCache).filter(DataCache.key == key).first()
    if row is None:
        row = DataCache(key=key, payload="{}")
        db.add(row)
    row.payload = json.dumps(payload)
    row.fetched_at = datetime.now(timezone.utc)
    db.commit()


def save_snapshot(db: Session, kind: str, payload: dict) -> None:
    today = date.today().isoformat()
    row = (
        db.query(ProbabilitySnapshot)
        .filter(ProbabilitySnapshot.kind == kind, ProbabilitySnapshot.snapshot_date == today)
        .first()
    )
    if row is None:
        row = ProbabilitySnapshot(kind=kind, snapshot_date=today, payload="{}")
        db.add(row)
    row.payload = json.dumps(payload)
    db.commit()


def list_snapshots(db: Session, kind: str, limit: int = 365) -> list[dict]:
    rows = (
        db.query(ProbabilitySnapshot)
        .filter(ProbabilitySnapshot.kind == kind)
        .order_by(ProbabilitySnapshot.snapshot_date.desc())
        .limit(limit)
        .all()
    )
    return [{"date": r.snapshot_date, **json.loads(r.payload)} for r in reversed(rows)]
