"""
Same-day fetch guard: prevents re-fetching data sources when the service
is restarted within the same calendar day.

Stores fetch records in SQLite (data_fetch_log table).
No external dependencies.
"""
from datetime import date
from typing import Optional
from sqlalchemy.orm import Session
from models import DataFetchLog


def should_fetch(db: Session, fetch_type: str) -> bool:
    """Return True if no completed fetch ("ok", or "partial" = ran but found nothing) is recorded today."""
    today = date.today().isoformat()
    existing = db.query(DataFetchLog).filter(
        DataFetchLog.fetch_type == fetch_type,
        DataFetchLog.fetched_date == today,
        DataFetchLog.status.in_(("ok", "partial")),
    ).first()
    return existing is None


def record_fetch(
    db: Session,
    fetch_type: str,
    record_count: int = 0,
    status: str = "ok",
    error_message: Optional[str] = None,
) -> DataFetchLog:
    """Record a fetch attempt in the log."""
    today = date.today().isoformat()
    log = DataFetchLog(
        fetch_type=fetch_type,
        fetched_date=today,
        record_count=record_count,
        status=status,
        error_message=error_message,
    )
    db.add(log)
    db.commit()
    return log


def last_fetch(db: Session, fetch_type: str) -> Optional[DataFetchLog]:
    """Return the most recent fetch log entry for this type, or None."""
    return (
        db.query(DataFetchLog)
        .filter(DataFetchLog.fetch_type == fetch_type)
        .order_by(DataFetchLog.created_at.desc())
        .first()
    )
