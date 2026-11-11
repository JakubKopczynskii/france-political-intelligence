"""
CAC40 scenario impact matrix and sentiment-driven probability signals.
Two impact methods:
  - factor:     sector sensitivities × illustrative macro shocks, scaled by revenue geography
  - historical: abnormal returns (vs DAX) in real French political episodes, mapped to scenarios
Not a forecast. Not investment advice.
"""
from datetime import date
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from cac40 import BY_TICKER
from database import get_db
from models import Company, PoliticalScenario, PriceCache
from services.scenario_engine import _get_sensitivity

router = APIRouter()

# Illustrative macro shocks per scenario slug.
# sovereign_spread: basis points; eur/energy: fractional (0.01 = 1%).
# No ECB policy-rate shock: a French election does not move the ECB rate directly;
# the French rate channel is carried by the sovereign spread.
SCENARIO_MACRO_SHOCKS: dict[str, dict[str, float]] = {
    "centrist": {
        "sovereign_spread": 20,
        "eur": 0.01,
        "energy": 0.05,
    },
    "national_rally": {
        "sovereign_spread": 120,
        "eur": -0.03,
        "energy": 0.10,
    },
    "left_wing": {
        "sovereign_spread": 80,
        "eur": -0.01,
        "energy": 0.15,
    },
    "hung_parliament": {
        "sovereign_spread": 150,
        "eur": -0.04,
        "energy": 0.0,
    },
}

SCENARIO_DISPLAY: dict[str, str] = {
    "centrist": "Centrist Continuity",
    "national_rally": "National Rally",
    "left_wing": "Left-Wing Coalition",
    "hung_parliament": "Hung Parliament",
}


def _company_impact_pct(sector: str, shocks: dict[str, float], ticker: str = "") -> float:
    """
    Return estimated equity impact (%) for a company given macro shocks.
    Uses revenue geography to give each company a unique sensitivity:
      - sovereign_spread: French political risk → scales with French revenue %
      - eur: exchange rate → scales with global (non-EUR) revenue %
      - energy: limited geographic variation
    Scaling factor: company_pct / baseline_pct, clamped to [0.3, 2.0].
    Baseline: 50% French, 50% global.
    """
    cdata = BY_TICKER.get(ticker, {})
    french_pct = cdata.get("french_pct", 50)
    global_pct = cdata.get("global_pct", 50)

    def _scale(raw: float, low: float = 0.3, high: float = 2.0) -> float:
        return max(low, min(high, raw))

    sov_scale    = _scale(french_pct / 50.0)          # French revenue baseline 50%
    eur_scale    = _scale(global_pct / 50.0)           # Global (non-EUR) revenue baseline 50%
    energy_scale = 1.0                                 # Energy sensitivity is sector-driven, not geographic

    total_return = 0.0
    scaled = {
        "sovereign_spread": shocks["sovereign_spread"] / 100,
        "eur": shocks["eur"],
        "energy": shocks["energy"],
    }
    factor_map = {
        "sovereign_spread": sov_scale,
        "eur": eur_scale,
        "energy": energy_scale,
    }
    for shock_type, shock_value in scaled.items():
        sensitivity = _get_sensitivity(shock_type, sector, {})
        total_return += sensitivity * shock_value * factor_map.get(shock_type, 1.0)
    return round(total_return * 100, 2)


def _get_live_prices(db: Session, tickers: list) -> dict:
    today = date.today().isoformat()
    rows = db.query(PriceCache).filter(PriceCache.ticker.in_(tickers), PriceCache.price_date == today).all()
    return {r.ticker: r.price for r in rows}


def index_impact(rows: list[dict], key: str) -> dict[str, float]:
    """CAC40-weighted index impact per scenario for impacts stored under rows[i][key]."""
    out: dict[str, float] = {}
    for slug in SCENARIO_MACRO_SHOCKS:
        vals = [(r["cac_weight"], r[key].get(slug)) for r in rows if r[key].get(slug) is not None]
        total_w = sum(w for w, _ in vals)
        if total_w:
            out[slug] = round(sum(w * v for w, v in vals) / total_w, 2)
    return out


def build_matrix(db: Session) -> dict:
    from services.historical import analog_impacts, analogs_meta
    from services.store import get_cache

    companies = db.query(Company).order_by(Company.name).all()
    live_prices = _get_live_prices(db, [c.ticker for c in companies])
    scenario_slugs = list(SCENARIO_MACRO_SHOCKS.keys())
    db_scenarios = {
        s.name: s for s in db.query(PoliticalScenario).filter(PoliticalScenario.name.in_(scenario_slugs)).all()
    }
    probs = {slug: (db_scenarios[slug].probability if slug in db_scenarios else 0.25) for slug in scenario_slugs}

    hist_cache = get_cache(db, "historical_episodes") or {}
    hist = analog_impacts(hist_cache) if hist_cache else {}
    episodes = hist_cache.get("episodes", [])

    scenarios_meta = []
    for slug in scenario_slugs:
        shocks = SCENARIO_MACRO_SHOCKS[slug]
        scenarios_meta.append({
            "slug": slug,
            "display_name": SCENARIO_DISPLAY.get(slug, slug),
            "probability": probs[slug],
            "prior_probability": db_scenarios[slug].prior_probability if slug in db_scenarios else None,
            "macro_shocks": {
                "sovereign_spread_bps": shocks["sovereign_spread"],
                "eur_pct": round(shocks["eur"] * 100, 1),
                "energy_pct": round(shocks["energy"] * 100, 1),
            },
        })

    rows = []
    for c in companies:
        cdata = BY_TICKER.get(c.ticker, {})
        impacts = {slug: _company_impact_pct(c.sector or "Unknown", shocks, ticker=c.ticker)
                   for slug, shocks in SCENARIO_MACRO_SHOCKS.items()}
        impacts_hist = {slug: hist[slug][c.ticker]["impact_pct"] for slug in hist if c.ticker in hist[slug]}
        imputed = any(hist[slug][c.ticker]["imputed"] for slug in hist if c.ticker in hist[slug])
        live_price = live_prices.get(c.ticker)
        rows.append({
            "ticker": c.ticker,
            "name": c.name,
            "sector": c.sector,
            "subsector": c.subsector,
            "impacts": impacts,
            "impacts_historical": impacts_hist,
            "historical_imputed": imputed,
            "expected_impact_pct": round(sum(impacts[s] * probs[s] for s in scenario_slugs), 2),
            "expected_impact_historical_pct": (
                round(sum(impacts_hist[s] * probs[s] for s in scenario_slugs), 2) if len(impacts_hist) == len(scenario_slugs) else None
            ),
            "episode_returns": {
                e["id"]: e["stocks"][c.ticker] for e in episodes if c.ticker in e["stocks"]
            },
            "cac_weight": cdata.get("index_weight", 0.0),
            "french_revenue_pct": cdata.get("french_pct", 50),
            "global_revenue_pct": cdata.get("global_pct", 50),
            "live_price": live_price,
        })

    rows.sort(key=lambda r: r["expected_impact_pct"], reverse=True)

    return {
        "scenarios": scenarios_meta,
        "companies": rows,
        "index_impact": {"factor": index_impact(rows, "impacts"), "historical": index_impact(rows, "impacts_historical")},
        "historical_available": bool(hist),
        "historical_computed_at": hist_cache.get("computed_at"),
        "analogs": analogs_meta(),
        "episodes": [{k: v for k, v in e.items() if k != "stocks"} for e in episodes],
        "methodology": (
            "Factor model: sector sensitivity × illustrative macro shock (spread, EUR, energy), scaled by each company's revenue geography. "
            "Historical analog: each stock's abnormal return versus the DAX (beta-adjusted) in real French political episodes, "
            "averaged over the episodes mapped to each scenario and scaled as listed. Not a forecast. Not investment advice."
        ),
        "disclaimer": (
            "Factor sensitivities and macro shocks are analyst assumptions. Historical analogs reflect how markets reacted to past "
            "events, which may not repeat. Not investment advice."
        ),
    }


@router.get("/api/analysis/cac40-matrix")
def get_cac40_matrix(db: Session = Depends(get_db)):
    """40 companies × 4 scenarios under both the factor model and historical analogs."""
    return build_matrix(db)


@router.get("/api/analysis/episodes")
def get_episodes(db: Session = Depends(get_db)):
    """Real French political episodes with per-stock raw and DAX-adjusted returns."""
    from services.store import get_cache
    cache = get_cache(db, "historical_episodes")
    if not cache:
        return {"available": False, "episodes": [], "message": "Historical episodes not computed yet — they are fetched on backend start."}
    companies = {
        c["ticker"]: {"name": c["name"], "sector": c["sector"], "weight": c["index_weight"]} for c in BY_TICKER.values()
    }
    return {"available": True, "computed_at": cache["computed_at"], "companies": companies, "episodes": cache["episodes"]}


@router.get("/api/analysis/sentiment")
async def get_sentiment_signals(db: Session = Depends(get_db)):
    """
    Returns current sentiment signals from RSS news, Reddit, and Google Trends,
    blended into scenario probability estimates.
    Sources: VADER NLP on cached news articles, Reddit public JSON API,
    Google Trends via pytrends.
    """
    from services.probability_engine import compute_probabilities
    return await compute_probabilities(db, persist=False)


@router.post("/api/analysis/extract-news")
async def extract_news_ai(db: Session = Depends(get_db)):
    """
    Run Groq extraction on up to 20 recent articles that have not been analysed yet and store the results.
    Only article title + snippet is sent to Groq — no user/portfolio data.
    """
    from services.groq_extractor import groq_available, run_extraction, _MODEL

    if not groq_available():
        return {"error": "GROQ_API_KEY not configured", "available": False}
    result = await run_extraction(db, limit=20)
    return {
        **result,
        "model": f"{_MODEL} (Groq)",
        "disclaimer": "AI extraction. Verify claims against primary sources.",
    }


@router.get("/api/analysis/covariance")
async def get_covariance(db: Session = Depends(get_db)):
    """
    Returns the cached historical covariance matrix for CAC40 tickers.
    Fetched once per day on startup via yfinance.
    """
    from services.covariance_fetcher import load_cached_covariance
    data = load_cached_covariance(db)
    if not data:
        return {"available": False, "message": "Covariance not yet fetched — restart backend to trigger fetch"}
    return {"available": True, **data}
