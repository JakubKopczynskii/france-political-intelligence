import json
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from database import get_db
from models import Company, CompanyExposure, PriceCache

router = APIRouter()


def _get_live_prices(db: Session, tickers: list[str]) -> dict[str, float | None]:
    """Fetch today's cached prices for a list of tickers."""
    today = date.today().isoformat()
    rows = (
        db.query(PriceCache)
        .filter(PriceCache.ticker.in_(tickers), PriceCache.price_date == today)
        .all()
    )
    return {r.ticker: r.price for r in rows}


def _serialize_company(c: Company, exposures: list = None, live_price: float | None = None) -> dict:
    result = {
        "id": c.id,
        "ticker": c.ticker,
        "isin": c.isin,
        "name": c.name,
        "sector": c.sector,
        "subsector": c.subsector,
        "listing_currency": c.listing_currency,
        "index_member": c.index_member,
        "french_revenue_pct": c.french_revenue_pct,
        "european_revenue_pct": c.european_revenue_pct,
        "global_revenue_pct": c.global_revenue_pct,
        "revenue_source": c.revenue_source,
        "is_synthetic_exposure": c.is_synthetic_exposure,
        "data_as_of": c.data_as_of.isoformat() if c.data_as_of else None,
        "live_price": live_price,
        "price_source": "Yahoo Finance (yfinance)" if live_price is not None else None,
        "data_quality_note": "Revenue geography data: null = unknown, not zero. Exposure data labelled synthetic where applicable.",
    }
    if exposures is not None:
        result["exposures"] = [
            {
                "id": e.id,
                "shock_type": e.shock_type,
                "sensitivity_coefficient": e.sensitivity_coefficient,
                "confidence": e.confidence,
                "source": e.source,
                "is_synthetic": e.is_synthetic,
                "rationale": e.rationale,
            }
            for e in exposures
        ]
    return result


@router.get("/api/companies")
def list_companies(
    sector: str = Query(None, description="Filter by sector"),
    search: str = Query(None, description="Search by name or ticker"),
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    q = db.query(Company)
    if sector:
        q = q.filter(Company.sector.ilike(f"%{sector}%"))
    if search:
        q = q.filter(
            (Company.name.ilike(f"%{search}%")) | (Company.ticker.ilike(f"%{search}%"))
        )
    total = q.count()
    companies = q.order_by(Company.sector, Company.name).offset(offset).limit(limit).all()
    tickers = [c.ticker for c in companies]
    prices = _get_live_prices(db, tickers)
    live_count = sum(1 for v in prices.values() if v is not None)
    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "companies": [_serialize_company(c, live_price=prices.get(c.ticker)) for c in companies],
        "live_prices": live_count > 0,
        "live_prices_count": live_count,
        "data_note": "CAC 40 constituents as of 2024. Verify current membership at Euronext. Revenue geography: unknown unless sourced.",
    }


@router.get("/api/companies/{ticker}")
def get_company(ticker: str, db: Session = Depends(get_db)):
    c = db.query(Company).filter(Company.ticker == ticker.upper()).first()
    if not c:
        raise HTTPException(status_code=404, detail=f"Company '{ticker}' not found")
    exposures = db.query(CompanyExposure).filter(CompanyExposure.company_id == c.id).all()
    prices = _get_live_prices(db, [c.ticker])
    return _serialize_company(c, exposures=exposures, live_price=prices.get(c.ticker))
