import json
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session
from database import get_db
from models import PoliticalScenario, ScenarioAssumption, ProbabilityRevision

router = APIRouter()


def _serialize_scenario(s: PoliticalScenario, include_assumptions: bool = False) -> dict:
    result = {
        "id": s.id,
        "name": s.name,
        "display_name": s.display_name,
        "description": s.description,
        "political_assumptions": json.loads(s.political_assumptions or "{}"),
        "policy_assumptions": json.loads(s.policy_assumptions or "{}"),
        "implementation_feasibility": s.implementation_feasibility,
        "feasibility_evidence": s.feasibility_evidence,
        "time_horizon": s.time_horizon,
        "economic_channels": json.loads(s.economic_channels or "[]"),
        "sector_sensitivities": json.loads(s.sector_sensitivities or "{}"),
        "fiscal_considerations": s.fiscal_considerations,
        "sources": json.loads(s.sources or "[]"),
        "invalidating_assumptions": json.loads(s.invalidating_assumptions or "[]"),
        "probability": s.probability,
        "probability_label": s.probability_label,
        "last_updated": s.last_updated.isoformat() if s.last_updated else None,
        "disclaimer": "This scenario is a hypothetical analytical framework. It is not a prediction of election results or policy outcomes.",
    }
    if include_assumptions:
        result["assumptions"] = [
            {
                "id": a.id,
                "category": a.category,
                "assumption_text": a.assumption_text,
                "information_type": a.information_type,
                "source_name": a.source_name,
                "source_url": a.source_url,
                "confidence": a.confidence,
                "is_editable": a.is_editable,
            }
            for a in s.assumptions
        ]
    return result


@router.get("/api/scenarios")
def list_scenarios(db: Session = Depends(get_db)):
    scenarios = db.query(PoliticalScenario).order_by(PoliticalScenario.probability.desc()).all()
    total_prob = sum(s.probability for s in scenarios)
    return {
        "scenarios": [_serialize_scenario(s) for s in scenarios],
        "total_probability": round(total_prob, 6),
        "probabilities_valid": abs(total_prob - 1.0) < 1e-4,
        "probability_note": "Scenario probabilities are illustrative analyst inputs, not statistical forecasts.",
    }


@router.get("/api/scenarios/compare")
def compare_scenarios(db: Session = Depends(get_db)):
    scenarios = db.query(PoliticalScenario).order_by(PoliticalScenario.probability.desc()).all()
    return {
        "scenarios": [_serialize_scenario(s, include_assumptions=True) for s in scenarios],
        "comparison_note": "These scenarios represent distinct analytical frameworks for how French politics could evolve. They are not exhaustive and their probabilities are illustrative.",
        "disclaimer": "Not investment advice. For analytical purposes only.",
    }


@router.get("/api/scenarios/{scenario_id}")
def get_scenario(scenario_id: int, db: Session = Depends(get_db)):
    s = db.query(PoliticalScenario).filter(PoliticalScenario.id == scenario_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Scenario not found")
    return _serialize_scenario(s, include_assumptions=True)


class ProbabilityUpdate(BaseModel):
    probability: float
    rationale: str = ""
    source: str = "analyst"

    @field_validator("probability")
    @classmethod
    def validate_prob(cls, v):
        if v < 0 or v > 1:
            raise ValueError("Probability must be between 0 and 1")
        return v


@router.patch("/api/scenarios/{scenario_id}/probability")
def update_scenario_probability(
    scenario_id: int,
    update: ProbabilityUpdate,
    db: Session = Depends(get_db),
):
    scenario = db.query(PoliticalScenario).filter(PoliticalScenario.id == scenario_id).first()
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")

    old_prob = scenario.probability
    scenario.probability = update.probability

    all_scenarios = db.query(PoliticalScenario).all()
    total = sum(s.probability for s in all_scenarios)

    if abs(total - 1.0) > 0.01:
        scenario.probability = old_prob
        db.rollback()
        raise HTTPException(
            status_code=422,
            detail=f"Probabilities would sum to {total:.4f}. All scenario probabilities must sum to 1.0. Adjust other scenarios first.",
        )

    # Log the revision for audit trail
    revision = ProbabilityRevision(
        scenario_id=scenario_id,
        old_probability=old_prob,
        new_probability=update.probability,
        source=update.source or "analyst",
        rationale=update.rationale or None,
    )
    db.add(revision)
    db.commit()

    return {
        "updated": True,
        "scenario_id": scenario_id,
        "old_probability": round(old_prob, 4),
        "new_probability": scenario.probability,
        "total_probability": round(total, 6),
        "note": "Probability is an illustrative analyst input, not a statistical forecast.",
    }


@router.get("/api/scenarios/{scenario_id}/probability-history")
def get_probability_history(scenario_id: int, db: Session = Depends(get_db)):
    scenario = db.query(PoliticalScenario).filter(PoliticalScenario.id == scenario_id).first()
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    revisions = (
        db.query(ProbabilityRevision)
        .filter(ProbabilityRevision.scenario_id == scenario_id)
        .order_by(ProbabilityRevision.revised_at.desc())
        .limit(50)
        .all()
    )
    return {
        "scenario_id": scenario_id,
        "scenario_name": scenario.name,
        "current_probability": scenario.probability,
        "revisions": [
            {
                "id": r.id,
                "old_probability": r.old_probability,
                "new_probability": r.new_probability,
                "source": r.source,
                "source_detail": r.source_detail,
                "rationale": r.rationale,
                "revised_at": r.revised_at.isoformat() if r.revised_at else None,
            }
            for r in revisions
        ],
    }


@router.get("/api/policies")
def list_policies(db: Session = Depends(get_db)):
    assumptions = db.query(ScenarioAssumption).all()
    scenarios = {s.id: s.display_name for s in db.query(PoliticalScenario).all()}
    return [
        {
            "id": a.id,
            "scenario_id": a.scenario_id,
            "scenario_name": scenarios.get(a.scenario_id, "Unknown"),
            "category": a.category,
            "assumption_text": a.assumption_text,
            "information_type": a.information_type,
            "source_name": a.source_name,
            "source_url": a.source_url,
            "confidence": a.confidence,
            "is_editable": a.is_editable,
        }
        for a in assumptions
    ]
