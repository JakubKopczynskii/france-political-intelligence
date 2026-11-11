> **Superseded (Nov 2026):** see [`docs/ENGINEERING_HANDOFF.md`](docs/ENGINEERING_HANDOFF.md) for the current architecture. Parts of this document are out of date.

# France Political Intelligence & CAC40 Portfolio Scenario Simulator
## Architecture & Methodology Reference

> **Disclaimer** — All scenario outputs, impact estimates, and probabilities in this system are illustrative analyst frameworks. They are not investment advice, election forecasts, or market predictions. See §13 for a full limitations statement.

---

## 1. What This System Does

This tool helps analysts and portfolio managers understand how different French political outcomes could affect CAC40 equities. It ingests public news, structures four distinct political scenarios (Centrist, National Rally, Left-Wing Coalition, Hung Parliament), and runs a deterministic linear factor model to estimate the equity impact on each of the 40 index constituents — and on any uploaded portfolio — under each scenario.

The goal is structured thinking, not prediction. The system forces you to be explicit about your assumptions, see which stocks are most exposed, and stress-test a portfolio before a political event materialises.

---

## 2. For Non-Technical Readers: How It Works

Think of it like a flight simulator for a portfolio.

A flight simulator doesn't predict what the weather will be. Instead, it lets a pilot ask: *"If we hit a sudden headwind of 50 knots, what happens to the plane?"* The answer isn't a forecast — it's structured preparation.

This system does the same thing for portfolios and politics:

1. **We define four possible futures** (the scenarios). Each has a name, a description of what it would mean politically, and a set of economic consequences (e.g. "spread widens 120 basis points, euro weakens 3%").

2. **We model how markets would react** using a simple rule: each sector responds differently to each type of shock. Banks are sensitive to sovereign spread widening. Energy companies benefit when oil prices rise. Luxury goods exporters gain when the euro weakens.

3. **We calculate the impact** on each of the 40 CAC40 stocks by multiplying that sensitivity by the size of the shock.

4. **We show the result** as a table of estimated gains/losses per stock per scenario — plus how a specific portfolio would look under each outcome.

The numbers are illustrative. The ranking and direction are what matter: *Which companies are most exposed? Which are defensive?*

---

## 3. Data Sources and What Leaves the Machine

| Data | Source | Leaves machine? | What is sent |
|---|---|---|---|
| News articles | RSS feeds (Le Monde, Reuters, Les Echos, ECB, Gouvernement.fr) | Yes | HTTP GET to each RSS URL |
| Market prices | Yahoo Finance via `yfinance` Python library | Yes | CAC40 ticker symbols only |
| Political probabilities | Polymarket public API (best-effort, no key required) | Yes | HTTP GET with `{"tag":"france"}` |
| Portfolio holdings | Local CSV import only | **Never** | Nothing — stays on disk |
| Scenario assumptions | Hardcoded in DB, analyst-editable | No | — |
| Company revenue data | Published annual reports (CSV import) | No | — |

**Security summary:** No portfolio data, no personal data, and no credentials are ever sent externally. The only external calls are: RSS fetch (news), `yfinance` (ticker symbols → prices), and Polymarket (a public markets query). All three are optional and fail gracefully.

---

## 4. The 4 Political Scenarios

| Slug | Display name | Default probability | Feasibility |
|---|---|---|---|
| `centrist` | Centrist Continuity | 35% | Medium |
| `national_rally` | National Rally | 25% | Medium |
| `left_wing` | Left-Wing Coalition (NFP/NUPES-style) | 25% | Low |
| `hung_parliament` | Hung Parliament / Political Deadlock | 15% | High |

### How probabilities work

Probabilities are **analyst inputs**, not statistical forecasts. They represent a human's structured judgement about the relative likelihood of each outcome. They must sum to 100%.

**Sources (in preference order):**
1. **Polymarket prediction markets** — if the system finds active French political markets on Polymarket at startup, it uses those prices (after normalisation to sum=1). These are crowd-sourced market prices, not official polls.
2. **Analyst manual input** — an analyst can update any scenario probability via `PATCH /api/scenarios/{id}/probability`. Every change is logged in the `probability_revision` audit table with timestamp, old value, new value, and optional rationale.
3. **Seed defaults** — if neither source provides data, the system uses the hardcoded defaults (35/25/25/15) labelled "illustrative analyst input".

The `probability_label` field on each scenario always tells you which source was used.

**What "illustrative" means:** The probabilities are structured expert judgement, not an objective measurement. Two analysts could assign different probabilities to the same scenario and both be defensible. The value of this system is forcing that judgement to be explicit and documented.

---

## 5. The CAC40 Impact Model

### In plain English

For each company, we estimate its equity impact under each scenario using this formula:

```
Impact (%) = sum over each shock type of:
    sector_sensitivity × shock_magnitude
```

For example, BNP Paribas (Financials sector) under the National Rally scenario:
- Sovereign spread widens +120 bps → Financials sensitivity is −1.5% per 1% (i.e. −0.015 per bp/100) → −1.8%
- EUR weakens −3% → Financials sensitivity is −0.1 per 1% → +0.3% (banks have mild benefit from EUR weakness)
- Energy prices +10% → Financials sensitivity is −0.03 per 1% → −0.3%
- **Net: −1.8%**

### The sensitivity table

Default sector sensitivities (these are fixed analyst assumptions, not empirically fitted):

| Shock type | Sector | Sensitivity | Interpretation |
|---|---|---|---|
| Sovereign spread | Financials | −1.5%/1% | Banks hurt most by spread widening |
| Sovereign spread | Real Estate | −1.2%/1% | Property exposed to rates |
| EUR change | Industrials | +0.4%/1% | Exporters benefit from weaker EUR |
| EUR change | Luxury (Cons. Disc.) | +0.3%/1% | Luxury exports gain from EUR weakness |
| Energy price | Energy sector | +0.80%/1% | Direct commodity benefit |
| Energy price | Industrials | −0.12%/1% | Input cost pressure |

The full table is in `backend/services/scenario_engine.py` → `_SECTOR_SENSITIVITIES`.

### What the numbers mean and don't mean

- **Relative ordering is meaningful:** A stock showing −3% vs another showing −0.5% under the same scenario is genuinely more exposed, based on its sector.
- **Absolute values are illustrative:** The sensitivity coefficients are analyst assumptions, not empirically calibrated regressions. The actual market reaction to a political shock will differ.
- **Expected impact** (the "WEIGHTED" column in the matrix) is the probability-weighted average across all 4 scenarios: `Σ(scenario_probability × scenario_impact)`.

---

## 6. Architecture (Technical)

### Component diagram

```
┌─────────────────────────────────────────────────────────────────┐
│  Browser (localhost:3000)                                       │
│  Next.js 14 App Router — 8 pages                                │
│  TypeScript + Tailwind + Recharts                               │
└──────────────────────────┬──────────────────────────────────────┘
                           │ HTTP (fetch, rewrites to :8000)
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│  FastAPI backend (localhost:8000)                               │
│  Python 3.10 · uvicorn · SQLAlchemy ORM                        │
│                                                                 │
│  Routers:                      Services:                        │
│  health / news / scenarios     rss_ingestion.py                 │
│  companies / portfolio         scenario_engine.py               │
│  stress_tests / ecb            price_fetcher.py (yfinance)      │
│  methodology / analysis        probability_fetcher.py           │
│                                cache_guard.py                   │
└──────────────────────────┬──────────────────────────────────────┘
                           │ SQLAlchemy
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│  SQLite database  (data/france_intel.db)                        │
│  Single file, local disk — never transmitted                    │
└─────────────────────────────────────────────────────────────────┘

External calls (optional, all gracefully degrade):
  ┌──────────────────┐  ┌──────────────────┐  ┌───────────────────┐
  │ RSS feeds        │  │ Yahoo Finance    │  │ Polymarket API    │
  │ 5 public feeds   │  │ via yfinance     │  │ gamma-api.        │
  │ Le Monde etc.    │  │ ticker prices    │  │ polymarket.com    │
  └──────────────────┘  └──────────────────┘  └───────────────────┘
```

### Tech stack

| Layer | Technology | Version |
|---|---|---|
| Frontend framework | Next.js App Router | 14.x |
| Frontend language | TypeScript | 5.x |
| UI styling | Tailwind CSS | 3.x |
| Charts | Recharts | 3.x |
| Backend framework | FastAPI | 0.11x |
| Backend language | Python | 3.10 |
| ORM | SQLAlchemy | 2.x |
| Database | SQLite | (bundled) |
| Data validation | Pydantic v2 | 2.x |
| HTTP client | aiohttp | (async RSS + Polymarket) |
| Market data | yfinance | 1.8.x |

---

## 7. Backend Services

| File | Purpose |
|---|---|
| `services/scenario_engine.py` | Pure functions: `apply_stress_shocks`, `run_monte_carlo`. No DB calls. |
| `services/rss_ingestion.py` | Fetches RSS feeds, deduplicates by SHA256 fingerprint, applies topic tags. |
| `services/price_fetcher.py` | Fetches CAC40 closing prices via yfinance; upserts into `price_cache` table. |
| `services/probability_fetcher.py` | Queries Polymarket API for French political markets; updates scenario probabilities if found. |
| `services/cache_guard.py` | Checks `data_fetch_log` table to skip re-fetches on same-day restarts. |

---

## 8. API Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/api/health` | System health, article/event count, last refresh time |
| GET | `/api/news` | List articles (filterable by topic, search, offset) |
| GET | `/api/news/{id}` | Single article |
| POST | `/api/news/refresh` | Trigger RSS feed refresh (background task) |
| GET | `/api/events` | List political events |
| GET | `/api/scenarios` | List all 4 scenarios with probabilities |
| PATCH | `/api/scenarios/{id}/probability` | Update probability (logs to audit table) |
| GET | `/api/scenarios/{id}/probability-history` | Audit log for probability changes |
| GET | `/api/companies` | List CAC40 companies (filterable) |
| GET | `/api/portfolio/demo` | Demo portfolio |
| POST | `/api/portfolio/import` | Import portfolio from CSV (local only) |
| POST | `/api/stress-tests/run` | Run deterministic stress test on a portfolio |
| GET | `/api/ecb` | ECB monetary policy scenarios |
| GET | `/api/methodology` | System methodology metadata |
| GET | `/api/analysis/cac40-matrix` | Full 40×4 scenario impact matrix |

---

## 9. Database Schema

| Table | Purpose | Key columns |
|---|---|---|
| `sources` | News source registry | name, url, quality_tier |
| `feeds` | RSS feed URLs per source | feed_url, last_fetched_at, health_status |
| `articles` | Fetched news articles | title, url, fingerprint, topic_tags, is_synthetic |
| `events` | Structured political events | headline, event_category, verification_status |
| `political_scenarios` | The 4 scenarios | name, probability, sector_sensitivities |
| `scenario_assumptions` | Assumptions backing each scenario | category, assumption_text, confidence |
| `probability_revision` | Audit log of probability changes | old/new probability, source, rationale |
| `companies` | CAC40 constituents | ticker, sector, revenue geography, is_synthetic_exposure |
| `company_exposures` | Per-company custom sensitivities (optional override) | shock_type, sensitivity_coefficient |
| `portfolios` | Imported or demo portfolios | name, total_value, is_demo |
| `holdings` | Portfolio positions | symbol, weight, market_value, sector |
| `stress_tests` | Stress test run records | shocks, methodology, run_at |
| `stress_test_results` | Stress test outputs | portfolio_pnl_pct, holding_contributions |
| `ecb_scenarios` | ECB monetary policy scenarios | profile_name, policy_rate_delta_bps |
| `price_cache` | Daily CAC40 closing prices | ticker, price, price_date |
| `data_fetch_log` | Same-day fetch guard | fetch_type, fetched_date, status |
| `ai_analyses` | AI analysis results (if enabled) | provider, facts_extracted |
| `forecasts` | Forward-looking forecasts | target_description, predicted_value |

---

## 10. Caching Strategy

The system must not re-fetch external data every time the server restarts (which would be slow, rate-limit Yahoo Finance, and produce duplicate DB writes).

**Mechanism:** The `data_fetch_log` table stores one row per `(fetch_type, fetched_date)` with `status = "ok"`. On startup, `cache_guard.should_fetch(db, fetch_type)` queries for a successful row with today's date. If one exists, the fetch is skipped.

**Fetch types:**
- `market_prices` — CAC40 closing prices via yfinance
- `polymarket_probs` — scenario probabilities from Polymarket
- `rss_feeds` — news articles from RSS feeds (manual trigger only; auto-refresh is POST `/api/news/refresh`)

**Behaviour on restart:**
- Same calendar day → skip → no external calls → startup in < 1 second
- New calendar day → fetch → prices and probabilities refresh in background → app is immediately usable, data arrives within ~10–30 seconds

News refresh is intentionally **not** auto-triggered at startup — it's triggered manually from the News page UI or via POST `/api/news/refresh` to avoid unnecessary load.

---

## 11. How to Run It

### First time (clean install)

```bash
# 1. Clone and enter project
cd /path/to/france-political-intelligence

# 2. Install Python dependencies
pip3 install -r backend/requirements.txt
pip3 install yfinance   # if not in requirements.txt

# 3. Start backend (auto-seeds DB on first run)
cd backend
uvicorn main:app --reload --port 8000

# 4. Install frontend dependencies (new terminal)
export PATH="/usr/local/lib/nodejs/node-v20.18.0-darwin-x64/bin:$PATH"
cd frontend
npm install

# 5. Start frontend dev server
npm run dev

# 6. Open http://localhost:3000
```

The backend seeds demo data automatically on first startup. You'll see "Seeding demo data..." in the backend terminal.

### Subsequent runs (existing DB)

```bash
# Terminal 1 — backend
cd backend && uvicorn main:app --reload --port 8000

# Terminal 2 — frontend
export PATH="/usr/local/lib/nodejs/node-v20.18.0-darwin-x64/bin:$PATH"
cd frontend && npm run dev
```

On restart with an existing DB, the backend:
- Skips seeding (scenarios already exist)
- Checks cache guard: skips price/probability fetch if already done today
- Launches background fetch tasks if it's a new calendar day

### Import revenue geography data (one-off)

```bash
cd /path/to/france-political-intelligence
python3 backend/scripts/import_revenue.py
```

This reads `data/cac40_revenue_geography.csv` and updates company revenue figures in the DB.

---

## 12. How to Add Real Data

### Real-time market prices
Already implemented. `yfinance` fetches CAC40 closing prices daily on startup. No action needed. Prices are stored in `price_cache` and can be queried via SQLite.

### Live scenario probabilities
Already implemented. Polymarket is queried daily on startup. If French political markets exist on Polymarket, probabilities are updated automatically. Probabilities can also be manually set via `PATCH /api/scenarios/{id}/probability`.

### Real news articles
Click **SCAN FEEDS** on the News page, or POST to `/api/news/refresh`. This triggers background fetches from all 5 configured RSS feeds. New articles appear within 30–60 seconds.

To add more RSS feeds, insert a row into `sources` and `feeds` tables (or extend `seed_data.py`).

### Real company revenue data
Edit `data/cac40_revenue_geography.csv` with sourced data, then re-run:
```bash
python3 backend/scripts/import_revenue.py
```
Data should be sourced from published annual reports. Mark the `source` and `data_as_of` columns accurately.

### Real portfolio
Go to the Portfolio page and import a CSV with columns:
```
symbol, quantity, market_value, currency, asset_type
```
Data stays local. It is never transmitted externally.

### AI-powered analysis (optional)
Set `ANTHROPIC_API_KEY=sk-...` in `backend/.env`. The system will use Claude to extract facts and interpretations from news articles. Without a key, the system falls back to deterministic tagging. **Never put API keys in frontend code.**

---

## 13. Known Limitations and Disclaimers

| Limitation | Detail |
|---|---|
| **Not investment advice** | Nothing in this system constitutes investment research, financial advice, or a solicitation to buy or sell securities. |
| **Sector sensitivities are illustrative** | The sensitivity coefficients in `_SECTOR_SENSITIVITIES` are analyst assumptions, not empirically fitted regressions. They have not been validated against historical data. |
| **Linear model only** | The impact model assumes linear, additive effects. Real equity markets exhibit non-linearity, tail effects, correlations, and second-order dynamics that this model ignores. |
| **Revenue geography is approximate** | The company revenue breakdown figures in `cac40_revenue_geography.csv` are sourced from published annual reports but are approximate. Companies report at different geographic granularities. |
| **Polymarket integration is best-effort** | If Polymarket has no active French political markets, the system silently keeps existing analyst probabilities. The `probability_label` field tells you which source is active. |
| **Demo mode** | Most news articles and events seeded at startup are synthetic (marked `is_synthetic = True`). Real articles require a manual news refresh. |
| **Probabilities are not forecasts** | Scenario probabilities represent structured analyst judgement, not statistical forecasts. They should not be quoted as probability estimates for real events. |
| **CAC40 composition** | The 40 companies in the system reflect the CAC40 as of 2024. Index composition changes over time. |
| **SQLite concurrency** | SQLite is single-writer. Under high concurrent load (not expected for a local analyst tool), use PostgreSQL instead. |
| **No authentication** | The API has no authentication layer. It is designed for local use only. Do not expose it to the internet without adding auth. |

---

*Last updated: 2026-11-08 | Version: 0.1.0 | Mode: MVP demo*
