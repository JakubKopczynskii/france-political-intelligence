"""
Background data jobs. Each job is guarded so it runs at most once per day
(historical episodes: once per week). `scheduler_loop` re-checks every 6 hours,
so data refreshes daily without restarting the backend.
"""
from __future__ import annotations
import asyncio
import logging
from datetime import datetime, timedelta, timezone

from database import SessionLocal
from services import cache_guard
from services.store import get_cache, set_cache, save_snapshot

log = logging.getLogger("jobs")
CHECK_INTERVAL_SECONDS = 6 * 3600


def sync_companies(db) -> int:
    """Align the companies table with cac40.py (fixes tickers seeded by older versions)."""
    from cac40 import CAC40
    from models import Company
    by_name = {c.name: c for c in db.query(Company).all()}
    changed = 0
    for entry in CAC40:
        row = by_name.get(entry["name"])
        if row is None:
            row = Company(ticker=entry["ticker"], name=entry["name"], sector=entry["sector"],
                          listing_currency="EUR", index_member="CAC40", is_synthetic_exposure=True)
            db.add(row)
        fields = {
            "ticker": entry["ticker"], "isin": entry["isin"], "sector": entry["sector"], "subsector": entry["subsector"],
            "french_revenue_pct": entry["french_pct"], "european_revenue_pct": entry["euro_pct"],
            "global_revenue_pct": entry["global_pct"], "revenue_source": "Approximate split from 2023 annual reports",
        }
        if any(getattr(row, k) != v for k, v in fields.items()):
            for k, v in fields.items():
                setattr(row, k, v)
            changed += 1
    db.commit()
    return changed


def restore_priors(db) -> None:
    """Fill prior_probability for scenarios created before the column existed."""
    from models import PoliticalScenario
    from seed_data import SCENARIO_PRIORS
    for row in db.query(PoliticalScenario).filter(PoliticalScenario.prior_probability == None).all():  # noqa: E711
        row.prior_probability = SCENARIO_PRIORS.get(row.name, row.probability)
    db.commit()


async def run_presidential_update() -> dict:
    from services import presidential
    pres = await asyncio.to_thread(presidential.run)
    with SessionLocal() as db:
        set_cache(db, "presidential", pres)
        save_snapshot(db, "presidential", {
            "p_win": {c["name"]: c["p_win"] for c in pres["candidates"] if c["p_win"] >= 0.001},
            "blocs": pres["blocs"],
        })
        cache_guard.record_fetch(db, "presidential_polls", pres["window"]["n_polls"])
    top = pres["candidates"][0]
    print(f"[jobs] Presidential polls: {pres['window']['n_polls']} recent polls, favourite {top['name']} {top['p_win']:.0%}")
    return pres


async def run_ai_extraction() -> None:
    from services.groq_extractor import groq_available, run_extraction
    if not groq_available():
        print("[jobs] AI extraction skipped — GROQ_API_KEY not set")
        return
    with SessionLocal() as db:
        result = await run_extraction(db, limit=30)
        cache_guard.record_fetch(db, "ai_extraction", result["saved"])
    print(f"[jobs] AI extraction: saved {result['saved']}/{result['processed']} articles")


async def run_signal_blend() -> None:
    from services.probability_engine import compute_probabilities
    with SessionLocal() as db:
        result = await compute_probabilities(db, persist=True)
        cache_guard.record_fetch(db, "signal_blend", len(result["sources_active"]))
    probs = {k: f"{v:.1%}" for k, v in result["probabilities"].items()}
    print(f"[jobs] Signal blend — sources: {result['sources_active']}, probs: {probs}")


async def run_historical(force: bool = False) -> None:
    from services import historical
    with SessionLocal() as db:
        cached = get_cache(db, "historical_episodes", max_age_hours=None if force else 24 * 7)
        if cached and not force:
            return
    data = await historical.compute()
    with SessionLocal() as db:
        set_cache(db, "historical_episodes", data)
    print(f"[jobs] Historical episodes computed: {len(data['episodes'])}")


async def run_market_risk() -> None:
    from services import market_risk
    data = await market_risk.compute()
    with SessionLocal() as db:
        set_cache(db, "market_risk", data)
        cache_guard.record_fetch(db, "market_risk", len(data["components"]))
    print(f"[jobs] Market risk gauge: {data['composite']['score']} ({data['composite']['label']})")


async def run_price_fetch() -> None:
    from services import price_fetcher
    with SessionLocal() as db:
        count = await price_fetcher.refresh_prices(db)
        cache_guard.record_fetch(db, "market_prices", count)
    print(f"[jobs] Price fetch: {count} tickers cached")


async def run_covariance_fetch() -> None:
    from models import Company
    from services.covariance_fetcher import refresh_covariance
    with SessionLocal() as db:
        tickers = [c.ticker for c in db.query(Company).all()]
        data = await refresh_covariance(db, tickers)
    print(f"[jobs] Covariance: {len(data.get('tickers', []))} tickers, {data.get('n_days')} trading days")


async def run_polymarket() -> None:
    from services import probability_fetcher
    with SessionLocal() as db:
        count = await probability_fetcher.refresh_scenario_probabilities(db)
        cache_guard.record_fetch(db, "polymarket_probs", count, "ok" if count else "partial")


async def _guarded(fetch_type: str, job, *args) -> None:
    with SessionLocal() as db:
        if not cache_guard.should_fetch(db, fetch_type):
            return
    try:
        await job(*args)
    except Exception as e:
        with SessionLocal() as db:
            cache_guard.record_fetch(db, fetch_type, 0, "error", str(e)[:500])
        print(f"[jobs] {fetch_type} failed: {e}")


async def _political_pipeline() -> None:
    # Order matters: the blend reads the poll simulation and stored AI extractions.
    await _guarded("presidential_polls", run_presidential_update)
    await _guarded("ai_extraction", run_ai_extraction)
    await _guarded("signal_blend", run_signal_blend)


async def run_due_jobs() -> None:
    await asyncio.gather(
        _guarded("market_prices", run_price_fetch),
        _guarded("covariance", run_covariance_fetch),
        _guarded("polymarket_probs", run_polymarket),
        _guarded("market_risk", run_market_risk),
        _guarded("historical_episodes", run_historical),
        _political_pipeline(),
    )


async def scheduler_loop() -> None:
    while True:
        try:
            await run_due_jobs()
        except Exception as e:
            print(f"[jobs] scheduler error: {e}")
        await asyncio.sleep(CHECK_INTERVAL_SECONDS)
