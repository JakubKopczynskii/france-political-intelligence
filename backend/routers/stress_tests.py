import json
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session
from database import get_db
from models import Portfolio, Holding, StressTest, StressTestResult
from services.scenario_engine import apply_stress_shocks, run_monte_carlo

router = APIRouter()


class MCParams(BaseModel):
    seed: int = 42
    n_paths: int = 1000
    horizon_days: int = 252
    expected_returns: Optional[list] = None
    volatilities: Optional[list] = None


class StressTestRequest(BaseModel):
    portfolio_id: int
    name: str = "Stress Test"
    scenario_id: Optional[int] = None
    shocks: dict  # {shock_type: value}
    methodology: str = "deterministic"
    mc_params: Optional[MCParams] = None


class StressTestResponse(BaseModel):
    test_id: int
    portfolio_pnl_pct: float
    portfolio_pnl_eur: float
    holding_contributions: list
    sector_contributions: list
    shocks_applied: dict
    methodology: str
    disclaimer: str


@router.post("/api/stress-tests/run")
def run_stress_test(request: StressTestRequest, db: Session = Depends(get_db)):
    portfolio = db.query(Portfolio).filter(Portfolio.id == request.portfolio_id).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    holdings = db.query(Holding).filter(Holding.portfolio_id == portfolio.id).all()
    if not holdings:
        raise HTTPException(status_code=400, detail="Portfolio has no holdings")

    holdings_data = [
        {
            "symbol": h.symbol,
            "weight": h.weight,
            "market_value": h.market_value,
            "sector": h.sector,
            "asset_type": h.asset_type,
        }
        for h in holdings
    ]

    # UI sends sovereign_spread/ecb_rate in bps and eur/energy as percentages.
    # Engine coefficients are calibrated per unit fraction (1.0 = 100 bps or 1%).
    scaled_shocks = {}
    for k, v in request.shocks.items():
        if k in ("sovereign_spread", "ecb_rate", "eur", "energy"):
            scaled_shocks[k] = v / 100
        else:
            scaled_shocks[k] = v
    result_data = apply_stress_shocks(holdings_data, scaled_shocks)

    mc_result = None
    var_95 = None
    es_95 = None
    mc_percentiles = None

    if request.methodology == "monte_carlo" and request.mc_params:
        n = len([h for h in holdings if h.asset_type != "cash"])
        weights = [h.weight for h in holdings if h.asset_type != "cash"]
        mc_p = request.mc_params

        expected_returns = mc_p.expected_returns or [0.07] * n
        volatilities = mc_p.volatilities or [0.20] * n

        if len(expected_returns) != n or len(volatilities) != n:
            raise HTTPException(
                status_code=422,
                detail=f"mc_params.expected_returns and volatilities must have {n} elements (one per equity holding)",
            )

        mc_result = run_monte_carlo(
            portfolio_weights=weights,
            expected_returns=expected_returns,
            volatilities=volatilities,
            n_paths=min(mc_p.n_paths, 10000),
            horizon_days=mc_p.horizon_days,
            seed=mc_p.seed,
        )
        var_95 = mc_result["var_95"]
        es_95 = mc_result["expected_shortfall_95"]
        mc_percentiles = json.dumps({
            "p5": mc_result["percentile_5"],
            "p50": mc_result["percentile_50"],
            "p95": mc_result["percentile_95"],
        })

    # Store test record
    stress_test = StressTest(
        name=request.name,
        portfolio_id=portfolio.id,
        scenario_id=request.scenario_id,
        shocks=json.dumps(request.shocks),
        methodology=request.methodology,
        mc_seed=request.mc_params.seed if request.mc_params else None,
        mc_paths=request.mc_params.n_paths if request.mc_params else None,
        mc_horizon_days=request.mc_params.horizon_days if request.mc_params else None,
        run_at=datetime.now(timezone.utc),
    )
    db.add(stress_test)
    db.flush()

    # Find best/worst
    holding_contribs = result_data["holding_contributions"]
    best = max(holding_contribs, key=lambda h: h["pnl_pct"], default=None)
    worst = min(holding_contribs, key=lambda h: h["pnl_pct"], default=None)

    test_result = StressTestResult(
        stress_test_id=stress_test.id,
        portfolio_pnl_pct=result_data["portfolio_pnl_pct"],
        portfolio_pnl_eur=result_data["portfolio_pnl_eur"],
        best_scenario_name=best["symbol"] if best else None,
        worst_scenario_name=worst["symbol"] if worst else None,
        holding_contributions=json.dumps(result_data["holding_contributions"]),
        sector_contributions=json.dumps(result_data["sector_contributions"]),
        var_95=var_95,
        expected_shortfall_95=es_95,
        mc_percentiles=mc_percentiles,
    )
    db.add(test_result)
    db.commit()

    response = {
        "test_id": stress_test.id,
        "portfolio_id": portfolio.id,
        "portfolio_name": portfolio.name,
        "portfolio_pnl_pct": result_data["portfolio_pnl_pct"],
        "portfolio_pnl_eur": result_data["portfolio_pnl_eur"],
        "holding_contributions": result_data["holding_contributions"],
        "sector_contributions": result_data["sector_contributions"],
        "shocks_applied": request.shocks,
        "methodology": request.methodology,
        "best_holding": best["symbol"] if best else None,
        "worst_holding": worst["symbol"] if worst else None,
        "disclaimer": "Stress test uses illustrative sensitivity assumptions. Not a forecast. Not investment advice.",
    }

    if mc_result:
        response["monte_carlo"] = {
            "var_95": var_95,
            "expected_shortfall_95": es_95,
            "percentile_5": mc_result["percentile_5"],
            "percentile_50": mc_result["percentile_50"],
            "percentile_95": mc_result["percentile_95"],
            "seed": mc_result["seed"],
            "n_paths": mc_result["n_paths"],
            "horizon_days": mc_result["horizon_days"],
            "methodology": mc_result["methodology"],
            "disclaimer": mc_result["disclaimer"],
        }

    return response


@router.get("/api/stress-tests")
def list_stress_tests(db: Session = Depends(get_db)):
    tests = db.query(StressTest).order_by(StressTest.run_at.desc()).limit(50).all()
    return [
        {
            "id": t.id,
            "name": t.name,
            "portfolio_id": t.portfolio_id,
            "methodology": t.methodology,
            "shocks": json.loads(t.shocks or "{}"),
            "run_at": t.run_at.isoformat() if t.run_at else None,
            "result": {
                "portfolio_pnl_pct": t.result.portfolio_pnl_pct,
                "portfolio_pnl_eur": t.result.portfolio_pnl_eur,
            } if t.result else None,
        }
        for t in tests
    ]


@router.get("/api/stress-tests/{test_id}")
def get_stress_test(test_id: int, db: Session = Depends(get_db)):
    t = db.query(StressTest).filter(StressTest.id == test_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Stress test not found")
    result = t.result
    return {
        "id": t.id,
        "name": t.name,
        "portfolio_id": t.portfolio_id,
        "scenario_id": t.scenario_id,
        "shocks": json.loads(t.shocks or "{}"),
        "methodology": t.methodology,
        "run_at": t.run_at.isoformat() if t.run_at else None,
        "result": {
            "portfolio_pnl_pct": result.portfolio_pnl_pct,
            "portfolio_pnl_eur": result.portfolio_pnl_eur,
            "holding_contributions": json.loads(result.holding_contributions or "[]"),
            "sector_contributions": json.loads(result.sector_contributions or "[]"),
            "var_95": result.var_95,
            "expected_shortfall_95": result.expected_shortfall_95,
            "mc_percentiles": json.loads(result.mc_percentiles) if result.mc_percentiles else None,
        } if result else None,
    }
