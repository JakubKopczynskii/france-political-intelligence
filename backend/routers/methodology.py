import os
from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from services.groq_extractor import _MODEL as GROQ_MODEL
from models import Article, Event, PoliticalScenario, StressTest, PriceCache, DataFetchLog

router = APIRouter()


@router.get("/api/methodology")
def get_methodology(db: Session = Depends(get_db)):
    from datetime import date
    article_count = db.query(Article).count()
    synthetic_count = db.query(Article).filter(Article.is_synthetic == True).count()
    event_count = db.query(Event).count()
    scenario_count = db.query(PoliticalScenario).count()
    test_count = db.query(StressTest).count()
    today = date.today().isoformat()
    live_prices_count = db.query(PriceCache).filter(PriceCache.price_date == today).count()
    ai_log = db.query(DataFetchLog).filter(DataFetchLog.fetch_type == "ai_extraction").order_by(DataFetchLog.created_at.desc()).first()
    signal_log = db.query(DataFetchLog).filter(DataFetchLog.fetch_type == "signal_blend").order_by(DataFetchLog.created_at.desc()).first()

    return {
        "version": "0.1.0",
        "methodology_name": "France Political Intelligence MVP",
        "data_cutoff": "2024-11-08",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "ai_provider": "groq" if os.environ.get("GROQ_API_KEY") else "none",
        "model": f"{GROQ_MODEL} (Groq)" if os.environ.get("GROQ_API_KEY") else "keyword_extractor_v0.1",
        "data_summary": {
            "total_articles": article_count,
            "synthetic_articles": synthetic_count,
            "live_articles": article_count - synthetic_count,
            "events": event_count,
            "scenarios": scenario_count,
            "stress_tests_run": test_count,
            "live_prices_today": live_prices_count,
            "ai_extraction_last_run": ai_log.created_at.isoformat() if ai_log else None,
            "signal_blend_last_run": signal_log.created_at.isoformat() if signal_log else None,
        },
        "information_types": {
            "verified_fact": "Supported by traceable primary or reliable secondary source",
            "reported_claim": "Asserted by a source but not independently verified",
            "model_interpretation": "AI or analyst interpretation of evidence",
            "assumption": "Explicit user or model input",
            "scenario": "Hypothetical state of the world",
            "forecast": "Quantified estimate with defined target, horizon, timestamp and methodology",
        },
        "evidence_hierarchy": [
            "1. Official laws, government decisions, ECB decisions, statistical releases",
            "2. Official party programmes and attributable speeches",
            "3. Reputable polling and established data providers",
            "4. Reputable news organizations",
            "5. Verified public statements on social platforms",
            "6. Unverified claims (remain unconfirmed)",
        ],
        "scenario_methodology": {
            "probabilities": "Blend of a fixed analyst prior (40%), a presidential poll simulation (35%), news extraction (15%), Reddit (5%) and Google Trends (5%). The prior is never overwritten.",
            "presidential": "Monte Carlo over Wikipedia-listed first-round poll hypotheses and head-to-head polls, with polling error widening with time to the vote.",
            "validation": "Probabilities must sum to 1.0 — validated in code",
            "source_policy": "Party platform positions require attributable, dated sources",
            "disclaimer": "Scenarios are hypothetical frameworks. Not election predictions.",
        },
        "financial_methodology": {
            "portfolio_calculation": "Deterministic: portfolio_return = sum(w_i * r_i)",
            "expected_return": "Scenario-weighted: expected_return = sum(p_s * R_s)",
            "stress_test": "Sensitivity-based: each shock applied to sector/holding sensitivities",
            "monte_carlo": "Log-normal daily returns, reproducible with fixed seed",
            "sensitivity_coefficients": "Calibrated against 2011 Eurozone crisis (OAT-Bund spread) and 2022-23 ECB hiking cycle.",
            "options": "Not supported in MVP. Equity positions only.",
            "double_counting_note": "Users should inspect transmission channels to avoid overlapping shocks",
        },
        "model_warnings": [
            "ECB successor profiles are hypothetical constructs, not predictions",
            "Scenario probabilities blend a fixed analyst prior with poll and news signals — not a calibrated election forecast",
            "Historical analogs assume markets react to future events as they did to past ones; episode mapping and scaling are analyst choices",
            "Monte Carlo covariance estimated from 1-year yfinance history — may not reflect current market regimes",
        ],
        "limitations": [
            f"Market prices fetched daily via Yahoo Finance — {live_prices_count} tickers cached today" if live_prices_count > 0 else "Market prices not yet fetched today — restart backend to trigger",
            "Scenario probabilities: fixed prior + presidential poll simulation + news extraction + Reddit + Google Trends, refreshed daily",
            "OAT–Bund spread is monthly (ECB); no free daily French yield source is used",
            f"AI news extraction: {'active via Groq ' + GROQ_MODEL if os.environ.get('GROQ_API_KEY') else 'set GROQ_API_KEY in backend/.env to enable'}",
            "No options/derivatives pricing — equity positions only",
            "No multi-user authentication — local use only",
            "Background jobs run in-process (6-hourly check, daily refresh) — no external job queue",
        ],
    }


@router.get("/api/model-runs")
def list_model_runs(db: Session = Depends(get_db)):
    tests = db.query(StressTest).order_by(StressTest.run_at.desc()).limit(20).all()
    return {
        "model_runs": [
            {
                "id": t.id,
                "type": "stress_test",
                "name": t.name,
                "methodology": t.methodology,
                "run_at": t.run_at.isoformat() if t.run_at else None,
                "portfolio_id": t.portfolio_id,
            }
            for t in tests
        ],
        "note": "Model run history shows stress tests executed. Forecast evaluation metrics will be available once forecast outcomes are recorded.",
    }
