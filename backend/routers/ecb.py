import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import ECBScenario

router = APIRouter()


def _serialize_ecb(e: ECBScenario) -> dict:
    return {
        "id": e.id,
        "profile_name": e.profile_name,
        "description": e.description,
        "policy_rate_delta_bps": e.policy_rate_delta_bps,
        "eur_impact_pct": e.eur_impact_pct,
        "oat_bund_spread_delta_bps": e.oat_bund_spread_delta_bps,
        "bank_margin_impact_pct": e.bank_margin_impact_pct,
        "is_verified_fact": e.is_verified_fact,
        "sources": json.loads(e.sources or "[]"),
        "last_updated": e.last_updated.isoformat() if e.last_updated else None,
        "disclaimer": "Successor profiles are hypothetical analytical constructs. No specific candidate is implied or predicted. ECB independence means actual decisions are data-driven.",
    }


@router.get("/api/ecb")
def list_ecb_scenarios(db: Session = Depends(get_db)):
    scenarios = db.query(ECBScenario).all()
    return {
        "scenarios": [_serialize_ecb(s) for s in scenarios],
        "context": {
            "module": "ECB and Christine Lagarde Succession Module",
            "purpose": "Scenario analysis tool for monetary policy uncertainty",
            "lagarde_mandate": "Christine Lagarde's ECB President mandate runs until November 2027 (illustrative — verify at ecb.europa.eu)",
            "disclaimer": "This module is for analytical purposes. ECB decisions are made by the Governing Council based on data. Successor profiles are generic and hypothetical.",
            "data_quality": "Policy rate and spread assumptions are illustrative. Use official ECB sources for actual decisions.",
            "official_source": "https://www.ecb.europa.eu",
        },
        "transmission_channels": [
            {"channel": "Policy rate", "description": "Direct impact on financing costs, mortgage rates, credit conditions"},
            {"channel": "EUR/USD", "description": "Currency impact on exporters, importers, euro-area inflation"},
            {"channel": "OAT-Bund spread", "description": "French sovereign risk premium, fiscal sustainability"},
            {"channel": "Bank margins", "description": "Net interest margin of eurozone banks"},
            {"channel": "Real estate", "description": "Discount rate sensitivity of property valuations"},
            {"channel": "Utilities/infrastructure", "description": "Long-duration asset valuation sensitivity"},
        ],
    }


@router.get("/api/ecb/{scenario_id}")
def get_ecb_scenario(scenario_id: int, db: Session = Depends(get_db)):
    s = db.query(ECBScenario).filter(ECBScenario.id == scenario_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="ECB scenario not found")
    return _serialize_ecb(s)
