"""
Historical return covariance estimation for Monte Carlo simulation.
Fetches 1 year of daily closes via yfinance, computes log-return covariance.

Outputs are stored as JSON in the DB (DataFetchLog value field) so they
survive restarts without re-fetching.
"""
from __future__ import annotations
import asyncio
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from sqlalchemy.orm import Session
from models import DataFetchLog

_LOOKBACK_DAYS = 365
_MIN_DAYS = 60  # minimum trading days required for a valid estimate


def _fetch_covariance_sync(tickers: list[str]) -> dict:
    """
    Fetch 1-year daily prices and compute annualised covariance matrix.
    Returns {tickers, cov_matrix, vol_vector, mean_return_vector, as_of}.
    """
    import yfinance as yf
    import numpy as np

    end = date.today()
    start = end - timedelta(days=_LOOKBACK_DAYS + 10)

    raw = yf.download(
        tickers,
        start=start.isoformat(),
        end=end.isoformat(),
        auto_adjust=True,
        progress=False,
        threads=True,
    )

    if raw.empty:
        raise ValueError("yfinance returned empty data")

    closes = raw["Close"] if isinstance(raw.columns, object) and "Close" in raw.columns else raw
    closes = closes.dropna(axis=1, thresh=_MIN_DAYS).dropna(axis=0, how="all")

    valid_tickers = list(closes.columns)
    log_returns = closes.pct_change().dropna()

    if len(log_returns) < _MIN_DAYS:
        raise ValueError(f"Only {len(log_returns)} trading days available")

    # Annualise: multiply daily cov by 252
    cov_daily = log_returns.cov().values
    cov_annual = (cov_daily * 252).tolist()
    vol_annual = (log_returns.std() * (252 ** 0.5)).tolist()
    mean_annual = (log_returns.mean() * 252).tolist()

    return {
        "tickers": valid_tickers,
        "cov_matrix": cov_annual,
        "vol_vector": vol_annual,
        "mean_return_vector": mean_annual,
        "n_days": len(log_returns),
        "as_of": end.isoformat(),
    }


async def fetch_covariance(tickers: list[str]) -> dict:
    """Async wrapper around the blocking yfinance fetch."""
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor(max_workers=1) as pool:
        return await loop.run_in_executor(pool, _fetch_covariance_sync, tickers)


def load_cached_covariance(db: Session) -> dict | None:
    """Load today's covariance from DB cache (DataFetchLog value field)."""
    row = (
        db.query(DataFetchLog)
        .filter(
            DataFetchLog.fetch_type == "covariance",
            DataFetchLog.fetched_date == date.today(),
            DataFetchLog.status == "ok",
        )
        .order_by(DataFetchLog.id.desc())
        .first()
    )
    if row and row.error_message:
        try:
            return json.loads(row.error_message)
        except Exception:
            pass
    return None


def save_covariance(db: Session, data: dict) -> None:
    """Persist covariance result in DataFetchLog (reusing error_message as value store)."""
    from services.cache_guard import record_fetch
    record_fetch(
        db,
        fetch_type="covariance",
        record_count=len(data.get("tickers", [])),
        status="ok",
        error_message=json.dumps(data),
    )


async def refresh_covariance(db: Session, tickers: list[str]) -> dict:
    """Fetch fresh covariance and cache it; return result."""
    data = await fetch_covariance(tickers)
    save_covariance(db, data)
    return data
