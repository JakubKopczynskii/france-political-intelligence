import asyncio
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

from database import engine, SessionLocal
from seed_data import create_tables, seed_demo_data
from models import PoliticalScenario

from routers import health, news, scenarios, companies, portfolio, stress_tests, ecb, methodology, analysis


async def _run_price_fetch():
    """Background task: fetch CAC40 market prices and cache them for today."""
    from database import SessionLocal as _SL
    from services import cache_guard, price_fetcher
    with _SL() as db:
        try:
            count = await price_fetcher.refresh_prices(db)
            cache_guard.record_fetch(db, "market_prices", count)
            print(f"[startup] Price fetch complete: {count} tickers cached")
        except Exception as e:
            with _SL() as db2:
                cache_guard.record_fetch(db2, "market_prices", 0, "error", str(e))
            print(f"[startup] Price fetch error: {e}")


async def _run_covariance_fetch():
    """Background task: fetch 1-year historical covariance for CAC40 tickers."""
    from database import SessionLocal as _SL
    from services import cache_guard
    from services.covariance_fetcher import refresh_covariance
    from models import Company
    with _SL() as db:
        try:
            tickers = [c.ticker for c in db.query(Company).all()]
            data = await refresh_covariance(db, tickers)
            print(f"[startup] Covariance fetched: {len(data.get('tickers', []))} tickers, {data.get('n_days')} trading days")
        except Exception as e:
            with _SL() as db2:
                cache_guard.record_fetch(db2, "covariance", 0, "error", str(e))
            print(f"[startup] Covariance fetch error: {e}")


async def _run_prob_fetch():
    """Background task: try to update scenario probabilities from Polymarket."""
    from database import SessionLocal as _SL
    from services import cache_guard, probability_fetcher
    with _SL() as db:
        try:
            count = await probability_fetcher.refresh_scenario_probabilities(db)
            status = "ok" if count > 0 else "partial"
            cache_guard.record_fetch(db, "polymarket_probs", count, status)
            if count > 0:
                print(f"[startup] Polymarket probs updated: {count} scenarios")
            else:
                print("[startup] Polymarket probs: no matching markets found, keeping existing values")
        except Exception as e:
            with _SL() as db2:
                cache_guard.record_fetch(db2, "polymarket_probs", 0, "error", str(e))
            print(f"[startup] Polymarket fetch error: {e}")


async def _run_signal_blend():
    """Background task: blend all sentiment signals and write probabilities to DB."""
    from database import SessionLocal as _SL
    from services import cache_guard
    from services.probability_engine import compute_probabilities
    with _SL() as db:
        try:
            result = await compute_probabilities(db)
            sources = result.get("sources_active", [])
            probs = result.get("probabilities", {})
            cache_guard.record_fetch(db, "signal_blend", len(sources))
            print(f"[startup] Signal blend complete — sources: {sources}, probs: { {k: f'{v:.1%}' for k,v in probs.items()} }")
        except Exception as e:
            print(f"[startup] Signal blend error: {e}")


async def _run_ai_extraction():
    """Background task: run Groq AI extraction on latest unprocessed articles."""
    from database import SessionLocal as _SL
    from services import cache_guard
    from services.groq_extractor import extract_articles_batch, groq_available
    from models import Article
    if not groq_available():
        print("[startup] AI extraction skipped — GROQ_API_KEY not set")
        return
    with _SL() as db:
        try:
            articles = (
                db.query(Article)
                .filter(Article.is_synthetic == False)
                .order_by(Article.published_at.desc())
                .limit(30)
                .all()
            )
            batch = [{"id": a.id, "title": a.title, "snippet": a.content_snippet or ""} for a in articles]
            results = await extract_articles_batch(batch, max_articles=30)
            cache_guard.record_fetch(db, "ai_extraction", len(results))
            print(f"[startup] AI extraction complete: {len(results)}/{len(batch)} articles processed")
        except Exception as e:
            print(f"[startup] AI extraction error: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure data directory exists
    _backend_dir = os.path.dirname(os.path.abspath(__file__))
    _data_dir = os.path.join(_backend_dir, "..", "data")
    os.makedirs(_data_dir, exist_ok=True)

    # Create tables (including any new ones added since last run)
    create_tables(engine)

    # Seed demo data if DB is empty
    with SessionLocal() as db:
        try:
            count = db.query(PoliticalScenario).count()
            if count == 0:
                print("Seeding demo data...")
                seed_demo_data(db)
                print("Demo data seeded.")
            else:
                print(f"DB already has {count} scenarios. Skipping seed.")
        except Exception as e:
            print(f"Seed error: {e}")

    # Auto-fetch data sources once per calendar day (cache guard skips if already done today)
    from services import cache_guard as _cg
    with SessionLocal() as db:
        if _cg.should_fetch(db, "market_prices"):
            asyncio.create_task(_run_price_fetch())
        else:
            print("[startup] Market prices already fetched today — skipping")

        if _cg.should_fetch(db, "polymarket_probs"):
            asyncio.create_task(_run_prob_fetch())
        else:
            print("[startup] Polymarket probs already fetched today — skipping")

        if _cg.should_fetch(db, "covariance"):
            asyncio.create_task(_run_covariance_fetch())
        else:
            print("[startup] Historical covariance already fetched today — skipping")

        if _cg.should_fetch(db, "signal_blend"):
            asyncio.create_task(_run_signal_blend())
        else:
            print("[startup] Signal blend already run today — skipping")

        if _cg.should_fetch(db, "ai_extraction"):
            asyncio.create_task(_run_ai_extraction())
        else:
            print("[startup] AI extraction already run today — skipping")

    yield


app = FastAPI(
    title="France Political Intelligence API",
    description="France Political Intelligence & CAC 40 Portfolio Scenario Simulator — MVP API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:3001", "http://127.0.0.1:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(news.router)
app.include_router(scenarios.router)
app.include_router(companies.router)
app.include_router(portfolio.router)
app.include_router(stress_tests.router)
app.include_router(ecb.router)
app.include_router(methodology.router)
app.include_router(analysis.router)


@app.get("/")
def root():
    return {
        "name": "France Political Intelligence API",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/api/health",
        "mode": "demo",
        "disclaimer": "MVP demo. All data labelled synthetic unless sourced. Not investment advice.",
    }
