"""
CAC40 scenario impact matrix and sentiment-driven probability signals.
Not a forecast. Not investment advice.
"""
from datetime import date
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from models import Company, PoliticalScenario, PriceCache
from services.scenario_engine import _get_sensitivity

router = APIRouter()

# CAC40 revenue geography (2023 annual reports) and index weights (% of CAC40 float-adj market cap, Nov 2024).
# french_pct + euro_pct + global_pct ≈ 100.
# index_weight: approximate % weight in the CAC40 index (sum ≈ 100).
_COMPANY_DATA: dict[str, dict] = {
    "AI.PA":     {"french_pct": 15, "euro_pct": 30, "global_pct": 55, "index_weight": 2.8},
    "AIR.PA":    {"french_pct": 15, "euro_pct": 40, "global_pct": 45, "index_weight": 7.0},
    "CS.PA":     {"french_pct": 25, "euro_pct": 40, "global_pct": 35, "index_weight": 2.5},
    "BNP.PA":    {"french_pct": 42, "euro_pct": 33, "global_pct": 25, "index_weight": 4.5},
    "EN.PA":     {"french_pct": 65, "euro_pct": 20, "global_pct": 15, "index_weight": 0.9},
    "CAP.PA":    {"french_pct": 15, "euro_pct": 35, "global_pct": 50, "index_weight": 1.5},
    "CA.PA":     {"french_pct": 45, "euro_pct": 30, "global_pct": 25, "index_weight": 1.0},
    "SGO.PA":    {"french_pct": 20, "euro_pct": 40, "global_pct": 40, "index_weight": 2.1},
    "ACA.PA":    {"french_pct": 65, "euro_pct": 25, "global_pct": 10, "index_weight": 2.2},
    "DSY.PA":    {"french_pct": 15, "euro_pct": 30, "global_pct": 55, "index_weight": 2.3},
    "EL.PA":     {"french_pct":  5, "euro_pct": 20, "global_pct": 75, "index_weight": 4.0},
    "EUFI.PA":   {"french_pct": 15, "euro_pct": 50, "global_pct": 35, "index_weight": 0.7},
    "RMS.PA":    {"french_pct": 10, "euro_pct": 15, "global_pct": 75, "index_weight": 8.5},
    "KER.PA":    {"french_pct":  8, "euro_pct": 15, "global_pct": 77, "index_weight": 2.6},
    "OR.PA":     {"french_pct":  5, "euro_pct": 20, "global_pct": 75, "index_weight": 5.0},
    "LR.PA":     {"french_pct": 15, "euro_pct": 30, "global_pct": 55, "index_weight": 1.3},
    "MC.PA":     {"french_pct": 10, "euro_pct": 15, "global_pct": 75, "index_weight": 11.2},
    "ML.PA":     {"french_pct": 10, "euro_pct": 25, "global_pct": 65, "index_weight": 1.4},
    "ORA.PA":    {"french_pct": 55, "euro_pct": 30, "global_pct": 15, "index_weight": 1.1},
    "RI.PA":     {"french_pct":  5, "euro_pct": 15, "global_pct": 80, "index_weight": 1.6},
    "PUB.PA":    {"french_pct":  5, "euro_pct": 15, "global_pct": 80, "index_weight": 2.4},
    "RNO.PA":    {"french_pct": 25, "euro_pct": 35, "global_pct": 40, "index_weight": 0.8},
    "SAF.PA":    {"french_pct": 15, "euro_pct": 25, "global_pct": 60, "index_weight": 3.5},
    "SAN.PA":    {"french_pct":  5, "euro_pct": 20, "global_pct": 75, "index_weight": 5.5},
    "SU.PA":     {"french_pct": 10, "euro_pct": 25, "global_pct": 65, "index_weight": 6.5},
    "GLE.PA":    {"french_pct": 50, "euro_pct": 30, "global_pct": 20, "index_weight": 2.0},
    "STLAM.MI":  {"french_pct": 10, "euro_pct": 40, "global_pct": 50, "index_weight": 1.8},
    "STM.PA":    {"french_pct":  5, "euro_pct": 15, "global_pct": 80, "index_weight": 1.2},
    "TEP.PA":    {"french_pct":  5, "euro_pct": 15, "global_pct": 80, "index_weight": 0.6},
    "HO.PA":     {"french_pct": 25, "euro_pct": 35, "global_pct": 40, "index_weight": 2.2},
    "TTE.PA":    {"french_pct":  5, "euro_pct": 20, "global_pct": 75, "index_weight": 9.1},
    "URW.AS":    {"french_pct": 25, "euro_pct": 50, "global_pct": 25, "index_weight": 0.5},
    "VIE.PA":    {"french_pct": 25, "euro_pct": 45, "global_pct": 30, "index_weight": 1.0},
    "DG.PA":     {"french_pct": 45, "euro_pct": 30, "global_pct": 25, "index_weight": 2.9},
    "VIV.PA":    {"french_pct": 50, "euro_pct": 25, "global_pct": 25, "index_weight": 0.4},
    "WLN.PA":    {"french_pct": 25, "euro_pct": 55, "global_pct": 20, "index_weight": 0.3},
    "MT.AS":     {"french_pct":  5, "euro_pct": 40, "global_pct": 55, "index_weight": 1.0},
    "EURAZ.PA":  {"french_pct": 60, "euro_pct": 25, "global_pct": 15, "index_weight": 0.3},
    "ALO.PA":    {"french_pct": 15, "euro_pct": 40, "global_pct": 45, "index_weight": 0.5},
    "ENGI.PA":   {"french_pct": 35, "euro_pct": 40, "global_pct": 25, "index_weight": 2.3},
}

# Illustrative macro shocks per scenario slug.
# sovereign_spread: basis points; eur/energy: fractional (0.01 = 1%).
SCENARIO_MACRO_SHOCKS: dict[str, dict[str, float]] = {
    "centrist": {
        "sovereign_spread": 20,
        "eur": 0.01,
        "ecb_rate": 0.0,
        "energy": 0.05,
    },
    "national_rally": {
        "sovereign_spread": 120,
        "eur": -0.03,
        "ecb_rate": 0.0,
        "energy": 0.10,
    },
    "left_wing": {
        "sovereign_spread": 80,
        "eur": -0.01,
        "ecb_rate": 0.0,
        "energy": 0.15,
    },
    "hung_parliament": {
        "sovereign_spread": 150,
        "eur": -0.04,
        "ecb_rate": 0.0,
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
      - ecb_rate: European interest rates → scales with French + European revenue %
      - energy: limited geographic variation
    Scaling factor: company_pct / baseline_pct, clamped to [0.3, 2.0].
    Baseline: 50% French, 50% global, 50% EU+French.
    """
    cdata = _COMPANY_DATA.get(ticker, {})
    french_pct = cdata.get("french_pct", 50)
    euro_pct   = cdata.get("euro_pct",   30)
    global_pct = cdata.get("global_pct", 50)

    def _scale(raw: float, low: float = 0.3, high: float = 2.0) -> float:
        return max(low, min(high, raw))

    sov_scale    = _scale(french_pct / 50.0)          # French revenue baseline 50%
    eur_scale    = _scale(global_pct / 50.0)           # Global (non-EUR) revenue baseline 50%
    ecb_scale    = _scale((french_pct + euro_pct) / 60.0)  # EU+France baseline 60%
    energy_scale = 1.0                                 # Energy sensitivity is sector-driven, not geographic

    total_return = 0.0
    scaled = {
        "sovereign_spread": shocks["sovereign_spread"] / 100,
        "eur": shocks["eur"],
        "ecb_rate": shocks["ecb_rate"] / 100,
        "energy": shocks["energy"],
    }
    factor_map = {
        "sovereign_spread": sov_scale,
        "eur": eur_scale,
        "ecb_rate": ecb_scale,
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


@router.get("/api/analysis/cac40-matrix")
def get_cac40_matrix(db: Session = Depends(get_db)):
    """
    Returns impact matrix: 40 companies × 4 political scenarios.
    Impact is estimated equity return (%) under illustrative macro shocks.
    Methodology: deterministic linear factor model using default sector sensitivities.
    """
    companies = db.query(Company).order_by(Company.name).all()
    tickers = [c.ticker for c in companies]
    live_prices = _get_live_prices(db, tickers)

    scenario_slugs = list(SCENARIO_MACRO_SHOCKS.keys())

    # Fetch scenario metadata (probability etc.) from DB
    db_scenarios = {
        s.name: s
        for s in db.query(PoliticalScenario).filter(
            PoliticalScenario.name.in_(scenario_slugs)
        ).all()
    }

    scenarios_meta = []
    for slug in scenario_slugs:
        shocks = SCENARIO_MACRO_SHOCKS[slug]
        db_s = db_scenarios.get(slug)
        scenarios_meta.append({
            "slug": slug,
            "display_name": SCENARIO_DISPLAY.get(slug, slug),
            "probability": db_s.probability if db_s else None,
            "macro_shocks": {
                "sovereign_spread_bps": shocks["sovereign_spread"],
                "eur_pct": round(shocks["eur"] * 100, 1),
                "ecb_rate_bps": shocks["ecb_rate"],
                "energy_pct": round(shocks["energy"] * 100, 1),
            },
        })

    rows = []
    for c in companies:
        sector = c.sector or "Unknown"
        cdata = _COMPANY_DATA.get(c.ticker, {})
        impacts: dict[str, float] = {}
        for slug, shocks in SCENARIO_MACRO_SHOCKS.items():
            impacts[slug] = _company_impact_pct(sector, shocks, ticker=c.ticker)

        # Probability-weighted expected impact
        expected_impact = sum(
            impacts[slug] * (db_scenarios[slug].probability if slug in db_scenarios else 0.25)
            for slug in scenario_slugs
        )

        live_price = live_prices.get(c.ticker)
        rows.append({
            "ticker": c.ticker,
            "name": c.name,
            "sector": c.sector,
            "subsector": c.subsector,
            "impacts": impacts,
            "expected_impact_pct": round(expected_impact, 2),
            "cac_weight": cdata.get("index_weight", 1.0),
            "french_revenue_pct": cdata.get("french_pct", 50),
            "global_revenue_pct": cdata.get("global_pct", 50),
            "live_price": live_price,
            "live_price_eur": live_price,
        })

    # Sort by expected impact descending (best first)
    rows.sort(key=lambda r: r["expected_impact_pct"], reverse=True)

    return {
        "scenarios": scenarios_meta,
        "companies": rows,
        "methodology": (
            "Illustrative deterministic linear factor model. "
            "Impact = Σ(sector_sensitivity × macro_shock). "
            "Sensitivities and shocks are illustrative analyst assumptions, "
            "not empirical estimates. Not a forecast. Not investment advice."
        ),
        "disclaimer": (
            "Sector sensitivities calibrated against 2011 Eurozone crisis and 2022-23 ECB hiking cycle. "
            "Macro shocks are illustrative analyst assumptions. Not investment advice."
        ),
    }


@router.get("/api/analysis/sentiment")
async def get_sentiment_signals(db: Session = Depends(get_db)):
    """
    Returns current sentiment signals from RSS news, Reddit, and Google Trends,
    blended into scenario probability estimates.
    Sources: VADER NLP on cached news articles, Reddit public JSON API,
    Google Trends via pytrends.
    """
    from services.probability_engine import compute_probabilities
    result = await compute_probabilities(db)
    return result


@router.post("/api/analysis/extract-news")
async def extract_news_ai(db: Session = Depends(get_db)):
    """
    Run Groq AI extraction on the most recent 20 unprocessed articles.
    Extracts: scenario signals, affected sectors, entities, sentiment, market relevance.
    Only article title + snippet is sent to Groq — no user/portfolio data.
    """
    from services.groq_extractor import extract_articles_batch, groq_available
    from models import Article

    if not groq_available():
        return {"error": "GROQ_API_KEY not configured", "available": False}

    articles = (
        db.query(Article)
        .order_by(Article.published_at.desc())
        .limit(20)
        .all()
    )
    batch = [{"id": a.id, "title": a.title, "snippet": a.content_snippet or ""} for a in articles]
    results = await extract_articles_batch(batch)

    return {
        "extracted": len(results),
        "results": results,
        "model": "llama-3.1-8b-instant (Groq)",
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
