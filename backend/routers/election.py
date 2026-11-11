"""2027 presidential election: poll simulation, market impact by winner, calendar, market stress, history."""
from __future__ import annotations
import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import PoliticalScenario, ProbabilityRevision
from services.store import get_cache, list_snapshots

router = APIRouter()

CALENDAR_SOURCE = "https://fr.wikipedia.org/wiki/%C3%89lection_pr%C3%A9sidentielle_fran%C3%A7aise_de_2027"

CALENDAR = [
    {"date": "2024-06-09", "title": "Assemblée nationale dissolved", "kind": "political",
     "detail": "Snap legislative elections follow; no bloc wins an absolute majority."},
    {"date": "2024-12-04", "title": "Barnier government censured", "kind": "political",
     "detail": "Start of a run of minority governments."},
    {"date": "2026-04-19", "title": "Retailleau designated LR candidate", "kind": "candidacy",
     "detail": "Chosen by a vote of Les Républicains members."},
    {"date": "2026-07-07", "title": "Le Pen appeal verdict", "kind": "legal",
     "detail": "Sentenced on appeal to 45 months of ineligibility, 30 of them suspended."},
    {"date": "2026-08-27", "title": "First candidates' debate (MEDEF–LCI)", "kind": "campaign",
     "detail": "Seven candidates debate at the MEDEF summer conference."},
    {"date": "2027-04-18", "title": "First round", "kind": "vote",
     "detail": "Top two candidates advance unless one wins an absolute majority."},
    {"date": "2027-05-02", "title": "Second round", "kind": "vote",
     "detail": "Macron is term-limited and cannot stand."},
]


def _presidential_with_impacts(db: Session, pres: dict) -> dict:
    from routers.analysis import build_matrix
    from services.presidential import BLOC_TO_SCENARIO

    matrix = build_matrix(db)
    idx = matrix["index_impact"]
    bloc_impacts = {}
    for bloc, slug in BLOC_TO_SCENARIO.items():
        bloc_impacts[bloc] = {
            "scenario": slug,
            "factor_pct": idx["factor"].get(slug),
            "historical_pct": idx["historical"].get(slug),
        }

    def expected(method: str) -> float | None:
        vals = [(pres["blocs"].get(b, 0.0), v[f"{method}_pct"]) for b, v in bloc_impacts.items()]
        if any(v is None for _, v in vals):
            return None
        total_p = sum(p for p, _ in vals) or 1.0
        return round(sum(p * v for p, v in vals) / total_p, 2)

    # Top movers per bloc so the UI can show who wins/loses under each winner
    movers = {}
    for bloc, slug in BLOC_TO_SCENARIO.items():
        key = "impacts_historical" if matrix["historical_available"] else "impacts"
        ranked = sorted((r for r in matrix["companies"] if slug in r[key]), key=lambda r: r[key][slug])
        movers[bloc] = {
            "worst": [{"ticker": r["ticker"], "name": r["name"], "impact_pct": r[key][slug]} for r in ranked[:5]],
            "best": [{"ticker": r["ticker"], "name": r["name"], "impact_pct": r[key][slug]} for r in ranked[-5:][::-1]],
            "method": "historical" if matrix["historical_available"] else "factor",
        }

    return {
        **pres,
        "market": {
            "bloc_impacts": bloc_impacts,
            "expected_index_pct": {"factor": expected("factor"), "historical": expected("historical")},
            "movers": movers,
            "note": "Each bloc's win is mapped to the matching scenario bucket (far right → National Rally, centre & right → "
                    "Centrist Continuity, left → Left-Wing Coalition). Index impact is the CAC40-weighted average of company impacts.",
        },
    }


@router.get("/api/election/presidential")
def get_presidential(db: Session = Depends(get_db)):
    pres = get_cache(db, "presidential")
    if not pres:
        return {"available": False, "message": "Poll simulation has not run yet — it runs on backend start, or POST /api/election/presidential/refresh."}
    return {"available": True, **_presidential_with_impacts(db, pres)}


@router.post("/api/election/presidential/refresh")
async def refresh_presidential(db: Session = Depends(get_db)):
    from services.jobs import run_presidential_update
    try:
        await run_presidential_update()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Poll refresh failed: {e}")
    return get_presidential(db)


@router.get("/api/election/calendar")
def get_calendar():
    return {"events": CALENDAR, "source": CALENDAR_SOURCE,
            "note": "Dates from the French Wikipedia article on the 2027 election. Intermediate deadlines are added once officially set."}


@router.get("/api/election/market-risk")
def get_market_risk(db: Session = Depends(get_db)):
    risk = get_cache(db, "market_risk")
    if not risk:
        return {"available": False, "message": "Market risk gauge not computed yet — it runs on backend start."}
    scenarios = {s.name: s.probability for s in db.query(PoliticalScenario).all()}
    pres = get_cache(db, "presidential") or {}
    disruptive = sum(scenarios.get(s, 0.0) for s in ("national_rally", "left_wing", "hung_parliament"))
    return {
        "available": True,
        **risk,
        "model_comparison": {
            "blended_disruptive_probability": round(disruptive, 4),
            "presidential_far_right_win": pres.get("blocs", {}).get("far_right"),
            "presidential_left_win": pres.get("blocs", {}).get("left"),
            "note": "Disruptive = National Rally + Left-Wing + Hung Parliament scenario probabilities. A high probability with a calm "
                    "market reading means markets are pricing less political risk than polls imply, or expect it to be contained.",
        },
    }


@router.get("/api/election/history")
def get_history(db: Session = Depends(get_db)):
    names = {s.id: s.name for s in db.query(PoliticalScenario).all()}
    revisions = (
        db.query(ProbabilityRevision).order_by(ProbabilityRevision.revised_at).all()
    )
    pres = get_cache(db, "presidential") or {}
    return {
        "scenario_snapshots": list_snapshots(db, "scenarios"),
        "presidential_snapshots": list_snapshots(db, "presidential"),
        "revisions": [
            {"date": r.revised_at.isoformat() if r.revised_at else None, "scenario": names.get(r.scenario_id),
             "old": r.old_probability, "new": r.new_probability, "source": r.source, "rationale": r.rationale}
            for r in revisions
        ],
        "poll_history": pres.get("history"),
    }
