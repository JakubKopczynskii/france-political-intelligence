# Engineering Handoff — France Political Intelligence

Written 2026-11-11 after commit `3e6b080`. This is the canonical description of the system; `ARCHITECTURE.md` and `docs/MVP_ARCHITECTURE_AND_NEXT_STEPS.md` predate it and are partly wrong.

Audience: an engineer or coding agent picking the project up cold. Read sections 1–3 before changing code, and section 6 before choosing what to build.

---

## 1. Product thesis

The **French presidential election is on 18 April / 2 May 2027**. Macron is term-limited. The question users care about: *which candidate wins, and what does that do to French stocks and my portfolio?*

The app answers in three layers:

1. **Who wins**: a two-round poll simulation from every published poll.
2. **What it does to markets**: two impact models per CAC 40 company (factor model and historical analog from real French shocks).
3. **What markets already price**: a stress gauge (OAT–Bund spread, CAC vs DAX, French vs EU banks).

The differentiator is that layer 2 is grounded in how these stocks actually moved in June 2024, Dec 2024 and Aug/Oct 2025, not in made-up sensitivities. Keep that property when extending.

### Snapshot on 2026-11-11 (live data)

| Metric | Value |
|---|---|
| Polls in 45-day window | 17 polls / 74 line-ups (85 first-round polls and 106 head-to-heads parsed in total) |
| P(win) | Le Pen 92.3%, Philippe 4.7%, Glucksmann 2.2%, Attal 0.3% |
| Most likely runoff | Le Pen vs Mélenchon 61% (Le Pen 67.5% in head-to-heads) |
| Blended scenario probabilities | National Rally 46.4%, Centrist 23.0%, Left 17.6%, Hung parliament 13.0% |
| CAC 40 impact if RN wins | Historical analog −5.3%; factor model −0.8% |
| Market stress gauge | 49/100 "Normal" (June 2024 dissolution = 84). OAT–Bund spread 147bp, the 5-year high (P100) |

---

## 2. Running and developing

```bash
bash start.sh                                    # both servers (backend :8000, frontend :3000)
cd backend && python3 -m pytest -q               # 55 tests
cd frontend && npx tsc --noEmit && npx next lint
```

Gotchas:
- **Secrets** live only in `backend/.env` (`GROQ_API_KEY`, optional `GROQ_MODEL`). Never commit, never put in frontend code. `rough_notes*` is the owner's private scratch file; it is gitignored and must never be staged.
- **Daily job guard**: every job writes a `data_fetch_log` row. A job with an `ok`/`partial` row for today is skipped. To force a re-run: `sqlite3 data/france_intel.db "delete from data_fetch_log where fetched_date=date('now') and fetch_type='signal_blend'"`, then restart.
- **Groq model churn**: `llama-3.1-8b-instant` was retired, which silently broke extraction. Default is now `openai/gpt-oss-20b`. Failures are logged as `[groq] extraction failed`. If extraction saves 0 articles, list models with `client.models.list()`.
- Under redirected output, run uvicorn with `PYTHONUNBUFFERED=1` or job `print`s won't appear.
- Running scripts outside uvicorn: `cd backend && PYTHONPATH=. python3 script.py`. `load_dotenv()` from stdin scripts fails, so pass `".env"` explicitly.
- Headless UI check without clicking: `/scenarios?tab=heatmap&method=historical` (also `replay`, `history`, `sentiment`). Chrome: `--headless=new --virtual-time-budget=15000 --screenshot`.
- Ticker gotchas on Yahoo: STMicro is `STMPA.PA`, Stellantis `STLAP.PA`, Eurofins `ERF.PA`, Eurazeo `RF.PA`, URW `URW.PA`, TotalEnergies `TTE.PA`.

---

## 3. Architecture

```
                    ┌──────────────── Next.js 14 (frontend/src) ─────────────────┐
                    │ /election  /scenarios(5 tabs)  /portfolio  /news  /companies│
                    │ /stress-test  /ecb  /methodology  / (overview)              │
                    └──────────────────────────┬──────────────────────────────────┘
                                               │ REST (lib/api.ts, types in lib/types.ts)
┌──────────────────────────────── FastAPI (backend) ──────────────────────────────────┐
│ routers/ election  analysis  portfolio  scenarios  news  companies  stress_tests ... │
│                                                                                      │
│ services/jobs.py  ── scheduler_loop (every 6h, each job ≤ once/day) ───────────────┐ │
│   market_prices → price_fetcher        covariance → covariance_fetcher            │ │
│   market_risk   → market_risk          historical_episodes → historical (weekly)  │ │
│   polymarket    → probability_fetcher                                             │ │
│   political pipeline (ordered): presidential → ai_extraction → signal_blend       │ │
│                                                                                    │ │
│ services/store.py: DataCache (JSON blobs) + ProbabilitySnapshot (daily)           │ │
└───────────────┬────────────────────────────────────────────────────────────────────┘
                │ SQLAlchemy
        data/france_intel.db (SQLite, gitignored)
External: fr.wikipedia.org · Yahoo Finance · ECB Data Portal · RSS · Groq · Reddit · Google Trends
```

### Backend modules

| File | Role |
|---|---|
| `cac40.py` | **Single source of truth** for the 40 constituents: ticker, ISIN, sector, revenue geography, normalised index weight. `jobs.sync_companies` aligns the DB to it on startup. |
| `main.py` | Lifespan: create tables, `_migrate_db` (PRAGMA-checked `ALTER TABLE`), seed, `restore_priors`, `sync_companies`, start `scheduler_loop`. |
| `services/jobs.py` | All background jobs and their ordering. |
| `services/presidential.py` | Wikipedia poll parser (`_grid` expands rowspan/colspan) and Monte Carlo simulation. |
| `services/historical.py` | `EPISODES`, `ANALOGS`, event study (`_compute_sync`), `analog_impacts`. |
| `services/market_risk.py` | ECB IRS monthly yields plus Yahoo daily proxies, percentile-ranked stress gauge. |
| `services/probability_engine.py` | `blend()` of fixed prior and signals. `compute_probabilities(db, persist)`. |
| `services/sentiment_fetcher.py` | News signal: stored Groq extractions first, whole-word keyword fallback, VADER only for English. |
| `services/groq_extractor.py` | `run_extraction` (skips analysed articles, saves to `ai_analyses`), `load_extractions`. |
| `services/store.py` | `get_cache/set_cache` (table `data_cache`), `save_snapshot/list_snapshots` (table `probability_snapshot`). |
| `routers/analysis.py` | `build_matrix(db)`: factor and historical impacts per company, index impact, analog metadata. Reused by the election router and portfolio exposure. |
| `routers/election.py` | Presidential (+ market impact by bloc), calendar (static list, verified against fr.wikipedia), market risk (+ model comparison), history. |
| `routers/portfolio.py` | `/election-exposure`: holding impacts (company → sector proxy → index proxy), scenario P&L, poll-weighted expectation. |

### Key endpoints

| Endpoint | Returns |
|---|---|
| `GET /api/election/presidential` | candidates, matchups, blocs, poll history, assumptions, `market.bloc_impacts/movers/expected_index_pct` |
| `POST /api/election/presidential/refresh` | re-scrape and re-simulate now |
| `GET /api/election/market-risk` | composite score, 3 components with series, model-vs-market comparison |
| `GET /api/election/history` | scenario and presidential snapshots, revision audit log, poll history |
| `GET /api/election/calendar` | static dated events |
| `GET /api/analysis/cac40-matrix` | per company `impacts`, `impacts_historical`, `episode_returns`, `cac_weight`; `index_impact`, `analogs`, `episodes` |
| `GET /api/analysis/episodes` | per-episode, per-stock raw and abnormal returns plus company weights |
| `GET /api/analysis/sentiment` | blended probabilities and per-source signals (**read-only**, does not persist) |
| `GET /api/portfolio/{id}/election-exposure` | per method: scenario %/€, expected, poll-weighted, worst scenario, detractors |

### Data model additions (Nov 2026)
- `political_scenarios.prior_probability`: fixed analyst prior (centrist .35, RN .25, left .25, hung .15 in `seed_data.SCENARIO_PRIORS`). **Never overwrite it from code**; it is what stops the blend compounding.
- `data_cache(key, payload, fetched_at)`: keys `presidential`, `historical_episodes`, `market_risk`.
- `probability_snapshot(kind, snapshot_date, payload)`: kinds `scenarios`, `presidential`, one row per day.
- `ai_analyses` is now populated (provider `groq`, `interpretations` holds the JSON extraction).

### Frontend
- Design tokens: bg `#090909`, surface `#101010`, border `#262626`, text `#F5F5F5`/`#929292`/`#606060`. Mono uppercase labels. Bloc colours: far right `#4C7BD9`, centre-right `#D9A441`, left `#D9488B`.
- `app/election/page.tsx`: countdown, bloc bar, candidate table, CAC impact by winning bloc, runoffs, poll trend, stress gauge, calendar, assumptions.
- `app/scenarios/page.tsx` (~900 lines, should be split): tabs Scenarios / Impact heatmap (factor ↔ historical toggle) / Replay / History / Signals. `viewMatrix` swaps `impacts` to the active method so child components stay method-agnostic.
- `components/scenarios/{ReplayTab,HistoryTab}.tsx`, `components/portfolio/ElectionExposure.tsx`.

---

## 4. Models in detail

### Presidential simulation (`services/presidential.py`)
- First-round input: each poll's hypotheses (pollsters test several line-ups). Window is the 45 days before the newest poll (expands if fewer than 4 polls). Weight per poll is `0.5^(age/21d)`, split evenly across its hypotheses.
- Each draw: pick a hypothesis, add `N(0, tf·(1.5+0.1·share))` per candidate, take the top two. `tf = 1 + min(days_to_R1,365)/365` (1.43 today).
- Runoff: head-to-head average over 120 days. RN aliases `{le pen, bardella, candidat rn}` share polls when one is missing. With no poll, estimate from each candidate's score vs RN, falling back to their bloc's average. σ = 4.0·tf (+4 if estimated).
- Blocs from party codes (`_PARTY_BLOC`, `_NAME_BLOC`). Bloc maps to a scenario bucket: far right → national_rally, centre & right → centrist, left → left_wing.

### Historical analog (`services/historical.py`)
- Abnormal return = raw − β·DAX, with β from 250 trading days pre-episode.
- `ANALOGS`: centrist = 2017 R1 + 2022 R2 (×1.0); RN = June 2024 dissolution (×1.5); left = 0.6·dissolution + 0.4·2024 leg R2 (×1.5, low confidence); hung = Barnier/Bayrou/Lecornu/2024 leg R2 (×1.0). Missing stock gets the sector mean (URW pre-2023).

### Blend (`services/probability_engine.py`)
`40% prior + 35% polls + 15% news + 5% reddit + 5% trends`. Missing sources hand their weight to the prior. The poll signal keeps hung parliament at its prior share (not a presidential outcome).

### Market stress (`services/market_risk.py`)
Percentile of today vs own history: spread (5y monthly, higher = stress), CAC−DAX 20d and FR banks−EXV1 20d (lower = stress). Composite = mean percentile. Reference = 2024-06-14.

---

## 5. Known issues and tech debt (ranked)

| # | Issue | Where | Impact |
|---|---|---|---|
| 1 | **Not mobile-responsive.** Fixed 200px sidebar, wide tables. LinkedIn traffic is mostly phones. | `components/layout/Sidebar.tsx`, all pages | Blocks virality |
| 2 | **Local-only.** Nobody can open a link. | deployment | Blocks virality |
| 3 | Polling error is assumed, not calibrated (no backtest vs 2017/2022 polls). Candidate errors are independent (no correlated bloc error), so it is likely overconfident (92%). | `presidential.simulate` | Credibility |
| 4 | Candidacy and legal uncertainty (e.g. Le Pen eligibility) only enters via pollsters' line-ups. | `presidential` | Credibility |
| 5 | Analog scaling/mapping are judgement calls; left-wing analog is weak; 8 episodes; windows differ (1 day vs 1 week). | `historical.ANALOGS` | Model risk |
| 6 | Wikipedia scraping is fragile (table layout changes, footnotes). Only one poll source. | `presidential.parse_polls` | Data risk |
| 7 | Blend weights arbitrary; hung-parliament bucket conceptually mismatched with a presidential race. | `probability_engine` | Conceptual |
| 8 | Overview page (`/`) does not feature the election; Scenarios header still shows a "SYNTHETIC" label. | `app/page.tsx`, `app/scenarios/page.tsx:822` | First impression |
| 9 | CAC composition and index weights static (Nov 2024); revenue geography approximate. | `cac40.py` | Accuracy |
| 10 | OAT–Bund spread monthly only. | `market_risk` | Gauge latency |
| 11 | Polymarket fetcher finds no markets; Reddit/Trends are weak signals. | `probability_fetcher`, fetchers | Noise |
| 12 | In-process scheduler duplicates work with multiple uvicorn workers. | `jobs.scheduler_loop` | Scale |
| 13 | `scenarios/page.tsx` ~900 lines; no frontend tests; no API integration tests. | frontend | Maintainability |
| 14 | Old docs stale (`ARCHITECTURE.md`, `docs/MVP_ARCHITECTURE_AND_NEXT_STEPS.md`). | docs | Confusion |

---

## 6. Roadmap: maximum utility and shareability

Ordered by (user value × shareability) ÷ effort. Items 1–4 are prerequisites for a LinkedIn launch.

### P0: make it shareable
1. **Public read-only deployment.** Frontend on Vercel. Backend on Fly.io/Render with Postgres (or a nightly static JSON export to a CDN, since nearly all data is daily). Disable `/api/portfolio/import` server-side in public mode.
2. **Mobile layout.** Collapsible sidebar (bottom tab bar under 768px). Cards instead of wide tables. Election page first.
3. **Client-side portfolio.** Parse the CSV in the browser and compute exposure there from the public matrix JSON, so holdings never touch a server. "Your data never leaves your browser" is a selling point.
4. **Share cards (OG images).** `/api/og/election` renders a 1200×630 PNG (Next `ImageResponse`): "Le Pen 92% · CAC 40 −5.3% if RN wins · Stress 49/100 · updated <date>". Per-page `og:image` meta so LinkedIn previews look great. Add a "Share" button with prefilled text.

### P1: make people come back
5. **Daily/weekly "French Election Risk Brief".** Auto-generated from snapshots: biggest probability moves, poll changes, stress gauge, top movers. Publish as a page plus email (Buttondown/Resend). This is the recurring LinkedIn content engine.
6. **Alerts.** Email/Telegram when P(win) moves more than 5pts, a new poll lands, or the stress gauge crosses 70.
7. **Candidate pages.** Programme (sourced), polls, runoff odds, "what their win does to each sector". These are highly shareable per candidate.
8. **Calibration and credibility.** Backtest the simulation on 2017 and 2022 polls (Wikipedia has them), fit σ, add a correlated bloc error, and publish the Brier score and a methodology page.
9. **French/English toggle.** The core audience is French.

### P2: depth
10. Scenario builder sliders (spread, EUR, energy) driving the heatmap live (previously deferred by the user).
11. Dynamic CAC weights from market caps; refresh constituents.
12. Daily OAT yields (Banque de France Webstat API key) and an OAT–Bund daily chart with event markers.
13. Prediction-market comparison when 2027 French election markets exist.
14. Legislative follow-on: model the likely dissolution after a presidential win, so hung parliament becomes a conditional branch rather than a peer scenario.
15. Embeddable widget (`<iframe>`) for journalists and bloggers.

---

## 7. Rules to keep

- Never send portfolio holdings to any external service. Document every new outbound data flow in README "Data sources".
- No secrets in git or frontend. Scan `git diff --cached` for `ghp_|gsk_|sk-` before every commit.
- Every number shown should trace to a source or a labelled assumption. Show both impact methods when they disagree.
- Keep `prior_probability` immutable; persist blends only from the daily job.
- Add a test with every model change (`backend/tests/test_election_models.py` has the fixtures and patterns).
