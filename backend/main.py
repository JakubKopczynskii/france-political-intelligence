import asyncio
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

import sqlalchemy
from database import engine, SessionLocal
from seed_data import create_tables, seed_demo_data
from models import PoliticalScenario

from routers import health, news, scenarios, companies, portfolio, stress_tests, ecb, methodology, analysis, election


def _migrate_db(eng):
    """Add columns that exist in models but are missing from an older SQLite DB."""
    migrations = [
        ("articles", "image_url", "VARCHAR(1024)"),
        ("political_scenarios", "prior_probability", "FLOAT"),
    ]
    with eng.connect() as conn:
        existing = {
            table: {row[1] for row in conn.execute(sqlalchemy.text(f"PRAGMA table_info({table})"))}
            for table in {t for t, _, _ in migrations}
        }
        for table, col, col_type in migrations:
            if col not in existing[table]:
                conn.execute(sqlalchemy.text(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}"))
                conn.commit()
                print(f"[migrate] Added column {table}.{col}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    from services import jobs

    os.makedirs(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"), exist_ok=True)
    create_tables(engine)
    _migrate_db(engine)

    with SessionLocal() as db:
        if db.query(PoliticalScenario).count() == 0:
            print("Seeding demo data...")
            seed_demo_data(db)
        jobs.restore_priors(db)
        changed = jobs.sync_companies(db)
        if changed:
            print(f"[startup] Synced {changed} companies with cac40.py")

    scheduler = asyncio.create_task(jobs.scheduler_loop())
    yield
    scheduler.cancel()


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
app.include_router(election.router)


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
