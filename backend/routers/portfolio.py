import csv
import io
import json
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Response
from sqlalchemy.orm import Session
from database import get_db
from models import Portfolio, Holding

logger = logging.getLogger(__name__)
router = APIRouter()

CSV_TEMPLATE = "symbol,quantity,market_value,currency,asset_type\nMC.PA,150,200000,EUR,equity\nTTE.PA,2000,120000,EUR,equity\n"


def _serialize_portfolio(p: Portfolio, holdings: list) -> dict:
    total_value = sum(h.market_value for h in holdings)
    sector_map: dict = {}
    for h in holdings:
        s = h.sector or "Unknown"
        sector_map.setdefault(s, 0.0)
        sector_map[s] += h.market_value

    return {
        "id": p.id,
        "name": p.name,
        "is_demo": p.is_demo,
        "total_value": total_value,
        "currency": p.currency,
        "source": p.source,
        "created_at": p.created_at.isoformat() if p.created_at else None,
        "holdings": [
            {
                "id": h.id,
                "symbol": h.symbol,
                "company_name": h.company_name,
                "quantity": h.quantity,
                "market_value": h.market_value,
                "weight": round(h.weight, 6),
                "currency": h.currency,
                "asset_type": h.asset_type,
                "sector": h.sector,
            }
            for h in holdings
        ],
        "sector_exposures": [
            {"sector": s, "value": round(v, 2), "weight": round(v / total_value, 6) if total_value > 0 else 0}
            for s, v in sorted(sector_map.items(), key=lambda x: -x[1])
        ],
        "weight_sum": round(sum(h.weight for h in holdings), 6),
        "disclaimer": "Demo portfolio uses synthetic data. Not real holdings. Not investment advice.",
    }


@router.get("/api/portfolio/demo")
def get_demo_portfolio(db: Session = Depends(get_db)):
    p = db.query(Portfolio).filter(Portfolio.is_demo == True).first()
    if not p:
        raise HTTPException(status_code=404, detail="Demo portfolio not found. Run seed data.")
    holdings = db.query(Holding).filter(Holding.portfolio_id == p.id).all()
    return _serialize_portfolio(p, holdings)


@router.get("/api/portfolio/{portfolio_id}/template")
def download_template():
    return Response(
        content=CSV_TEMPLATE,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=portfolio_template.csv"},
    )


@router.post("/api/portfolio/import")
async def import_portfolio(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files accepted")

    content = await file.read()
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File encoding error. Use UTF-8.")

    reader = csv.DictReader(io.StringIO(text))
    required_cols = {"symbol", "market_value"}
    if not reader.fieldnames or not required_cols.issubset(set(f.strip().lower() for f in reader.fieldnames)):
        raise HTTPException(status_code=400, detail=f"CSV must have columns: {required_cols}. Got: {reader.fieldnames}")

    rows = []
    errors = []
    seen_symbols: set = set()

    for i, row in enumerate(reader, 1):
        row = {k.strip().lower(): v.strip() for k, v in row.items()}
        symbol = row.get("symbol", "").strip().upper()
        if not symbol:
            errors.append(f"Row {i}: symbol is empty")
            continue
        if symbol in seen_symbols:
            errors.append(f"Row {i}: duplicate symbol '{symbol}'")
            continue
        seen_symbols.add(symbol)

        try:
            market_value = float(row.get("market_value", "0"))
            if market_value <= 0:
                errors.append(f"Row {i}: market_value must be positive, got '{row.get('market_value')}'")
                continue
        except (ValueError, TypeError):
            errors.append(f"Row {i}: market_value must be numeric, got '{row.get('market_value')}'")
            continue

        quantity = None
        if row.get("quantity"):
            try:
                quantity = float(row["quantity"])
            except ValueError:
                errors.append(f"Row {i}: quantity must be numeric, got '{row['quantity']}'")
                continue

        rows.append({
            "symbol": symbol,
            "quantity": quantity,
            "market_value": market_value,
            "currency": row.get("currency", "EUR").upper(),
            "asset_type": row.get("asset_type", "equity").lower(),
        })

    if errors:
        raise HTTPException(status_code=422, detail={"validation_errors": errors})

    if not rows:
        raise HTTPException(status_code=400, detail="No valid rows found in CSV")

    total_value = sum(r["market_value"] for r in rows)
    if total_value <= 0:
        raise HTTPException(status_code=400, detail="Total portfolio value must be positive")

    # Normalize weights
    for r in rows:
        r["weight"] = r["market_value"] / total_value

    weight_sum = sum(r["weight"] for r in rows)
    if abs(weight_sum - 1.0) > 1e-4:
        logger.warning(f"Imported portfolio weights sum to {weight_sum:.6f} — normalizing")
        for r in rows:
            r["weight"] = r["weight"] / weight_sum

    portfolio = Portfolio(
        name=f"Imported: {file.filename}",
        is_demo=False,
        total_value=total_value,
        currency="EUR",
        source="csv_import",
        created_at=datetime.now(timezone.utc),
    )
    db.add(portfolio)
    db.flush()

    for r in rows:
        holding = Holding(
            portfolio_id=portfolio.id,
            symbol=r["symbol"],
            company_name=r["symbol"],
            quantity=r["quantity"],
            market_value=r["market_value"],
            weight=r["weight"],
            currency=r["currency"],
            asset_type=r["asset_type"],
        )
        db.add(holding)

    db.commit()

    holdings = db.query(Holding).filter(Holding.portfolio_id == portfolio.id).all()
    return {
        "imported": True,
        "portfolio_id": portfolio.id,
        "row_count": len(rows),
        "total_value": total_value,
        "privacy_note": "Portfolio data stored locally. Not sent to any external service.",
        **_serialize_portfolio(portfolio, holdings),
    }


@router.get("/api/portfolio/{portfolio_id}")
def get_portfolio(portfolio_id: int, db: Session = Depends(get_db)):
    p = db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    holdings = db.query(Holding).filter(Holding.portfolio_id == p.id).all()
    return _serialize_portfolio(p, holdings)


@router.delete("/api/portfolio/{portfolio_id}")
def delete_portfolio(portfolio_id: int, db: Session = Depends(get_db)):
    p = db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    if p.is_demo:
        raise HTTPException(status_code=400, detail="Cannot delete demo portfolio. Use reset endpoint.")
    db.query(Holding).filter(Holding.portfolio_id == portfolio_id).delete()
    db.delete(p)
    db.commit()
    return {"deleted": True, "portfolio_id": portfolio_id}
