# France Political Intelligence & CAC 40 Portfolio Scenario Simulator
## MVP Architecture & Next Steps

> Version 0.1.0 — Local MVP · All scenario data is illustrative analyst input

---

## 1. System Overview

```mermaid
graph TD
    subgraph "Browser (localhost:3000)"
        UI["Next.js 14 Frontend\n8 screens — React/TypeScript/Tailwind"]
    end

    subgraph "Local Backend (localhost:8000)"
        API["FastAPI REST API\n/api/* endpoints"]
        SE["Scenario Engine\nPure deterministic Python"]
        RSS["RSS Ingestion\naiohttp + feedparser"]
        AI["AI Adapter\nProvider-neutral (default: none)"]
        DB["SQLite\nfrance_intel.db"]
    end

    subgraph "Optional"
        MCP["MCP Server\nStdio JSON-RPC\n12 read-only tools"]
        EXT["External RSS Feeds\n17 sources configured"]
        LLM["AI Provider\nGemini / Groq / OpenRouter"]
    end

    UI -->|HTTP fetch| API
    API --> SE
    API --> RSS
    API --> AI
    API --> DB
    RSS -->|async fetch| EXT
    AI -->|optional API call| LLM
    MCP -->|HTTP| API
```

---

## 2. Component Architecture

```mermaid
graph LR
    subgraph "Frontend — src/app/"
        P1["/\nOverview"]
        P2["/news\nNews Intelligence"]
        P3["/scenarios\nPolitical Scenarios"]
        P4["/companies\nCAC 40 Universe"]
        P5["/portfolio\nPortfolio"]
        P6["/stress-test\nStress Testing"]
        P7["/ecb\nECB Module"]
        P8["/methodology\nMethodology"]
    end

    subgraph "Frontend — shared"
        API_CLIENT["lib/api.ts\nFetch client"]
        TYPES["lib/types.ts\nTypeScript interfaces"]
        SIDEBAR["Sidebar.tsx"]
        HEADER["Header.tsx"]
        DEMO["DemoLabel.tsx"]
        INFO["InfoTypeLabel.tsx"]
    end

    P1 & P2 & P3 & P4 & P5 & P6 & P7 & P8 --> API_CLIENT
    P1 & P2 & P3 & P4 & P5 & P6 & P7 & P8 --> HEADER
    API_CLIENT --> TYPES
```

---

## 3. Backend Module Map

```mermaid
graph TD
    subgraph "FastAPI Application — main.py"
        HEALTH["/api/health"]
        NEWS["/api/news\n/api/events\n/api/feeds/refresh"]
        SCEN["/api/scenarios\n/api/scenarios/probabilities"]
        COMP["/api/companies\n/api/companies/:id/exposure"]
        PORT["/api/portfolio\n/api/portfolio/import"]
        STRESS["/api/stress-tests/run\n/api/stress-tests"]
        ECB["/api/ecb/scenarios"]
        METH["/api/methodology"]
    end

    subgraph "Services"
        SE["scenario_engine.py\nvalidate_scenario_probabilities()\ncalculate_portfolio_return()\napply_stress_shocks()\nrun_monte_carlo()"]
        RSS_SVC["rss_ingestion.py\ncompute_fingerprint()\nfetch_feed()\napply_topic_tags()\ndetect_duplicates_in_batch()"]
        AI_SVC["ai_adapter.py\nAIProvider enum\ndeterministic_extract()\nanalyze_article()"]
    end

    subgraph "Data Layer"
        MODELS["models.py\n16 SQLAlchemy models"]
        SEED["seed_data.py\nseed_demo_data()\nreset_demo_data()"]
        DB2["SQLite\nfrance_intel.db"]
    end

    NEWS --> RSS_SVC
    NEWS --> AI_SVC
    SCEN & PORT & STRESS --> SE
    HEALTH & NEWS & SCEN & COMP & PORT & STRESS & ECB & METH --> MODELS
    MODELS --> DB2
    SEED --> DB2
```

---

## 4. Data Flow — RSS Ingestion

```mermaid
sequenceDiagram
    participant UI as Frontend
    participant API as FastAPI
    participant RSS as rss_ingestion.py
    participant EXT as External RSS
    participant AI as AI Adapter
    participant DB as SQLite

    UI->>API: POST /api/feeds/refresh
    API->>RSS: fetch_all_configured_feeds()
    loop For each of 17 configured feeds
        RSS->>EXT: HTTP GET feed_url (aiohttp, timeout=30s)
        EXT-->>RSS: RSS/Atom XML
        RSS->>RSS: parse entries (feedparser)
        RSS->>RSS: compute_fingerprint(url, title) → SHA256
        RSS->>DB: check existing fingerprints (dedup)
        RSS->>RSS: apply_topic_tags(title, content)
        RSS->>AI: analyze_article() [deterministic fallback if AI_PROVIDER=none]
        RSS->>DB: INSERT Article, Event (if political keywords match)
    end
    API-->>UI: {ingested: N, skipped_duplicates: M}
```

---

## 5. Data Flow — Portfolio Stress Test

```mermaid
sequenceDiagram
    participant UI as Frontend
    participant API as FastAPI
    participant SE as scenario_engine.py
    participant DB as SQLite

    UI->>API: POST /api/stress-tests/run\n{portfolio_id, shocks: {sovereign_spread, eur, ecb_rate, energy}}
    API->>DB: load Portfolio + Holdings
    API->>DB: load CompanyExposure for each holding
    API->>SE: apply_stress_shocks(holdings, shocks)
    Note over SE: Pure deterministic — no DB calls<br/>Applies sector sensitivities<br/>sovereign: Banks, Utilities, Real Estate<br/>eur: Industrials, Luxury, Energy<br/>ecb_rate: Real Estate, Banks, Utilities<br/>energy: Materials, Industrials, Utilities
    SE-->>API: {portfolio_pnl_pct, portfolio_pnl_eur,\nholding_contributions, sector_contributions}
    API->>SE: run_monte_carlo(weights, expected_returns, volatilities, seed=42)
    SE-->>API: {percentile_5, percentile_50, percentile_95,\nvar_95, expected_shortfall_95}
    API->>DB: INSERT StressTest + StressTestResults
    API-->>UI: StressTestResponse (full results)

    Note over UI: Portfolio data NEVER sent to any AI provider
```

---

## 6. Entity-Relationship Diagram

```mermaid
erDiagram
    Source ||--o{ Feed : "provides"
    Feed ||--o{ Article : "contains"
    Article ||--o{ Event : "generates"
    Article ||--o{ AIAnalysis : "has"

    PoliticalScenario ||--o{ ScenarioAssumption : "has"
    PoliticalScenario ||--o{ Forecast : "informs"

    Company ||--o{ CompanyExposure : "has"
    Company ||--o{ Holding : "held_in"

    Portfolio ||--o{ Holding : "contains"
    Portfolio ||--o{ StressTest : "tested_by"

    StressTest ||--o{ StressTestResult : "produces"

    ECBScenario {
        string name
        string candidate_name
        float hawkish_score
        float impact_sovereign_spread
    }

    PoliticalScenario {
        string slug
        float probability
        string display_name
        string implementation_feasibility
    }

    CompanyExposure {
        string factor
        float sensitivity
        string direction
        string information_type
    }

    Holding {
        float weight
        float quantity
        float purchase_price
        string sector
    }
```

---

## 7. AI Provider Abstraction

```mermaid
graph LR
    subgraph "ai_adapter.py"
        ENV["AI_PROVIDER env var\ndefault: none"]
        ROUTER{Provider\nrouter}
        DET["deterministic_extract()\nis_ai_generated=False\nKeyword-based tagging"]
        GEM["Gemini API\ngemini-pro"]
        GROQ["Groq API\nllama-3.1-70b-versatile"]
        OR["OpenRouter\nany model"]
    end

    ENV --> ROUTER
    ROUTER -->|none| DET
    ROUTER -->|gemini| GEM
    ROUTER -->|groq| GROQ
    ROUTER -->|openrouter| OR

    note1["All AI analysis is\nlabeled model_interpretation\nnever verified_fact"]
    note2["Portfolio data\nNEVER sent to\nany AI provider"]
```

---

## 8. Information Type Taxonomy

```mermaid
graph TD
    subgraph "6 Information Types (brief Section 10)"
        VF["verified_fact\n🟢 Green\nTraceable primary source"]
        RC["reported_claim\n🔵 Blue\nAsserted but not verified"]
        MI["model_interpretation\n🟣 Purple\nAI or analyst interpretation"]
        AS["assumption\n🟡 Amber\nExplicit user/model input"]
        SC["scenario\n🔵 Teal\nHypothetical world state"]
        FC["forecast\n🟠 Orange\nProjected future state"]
    end
```

---

## 9. Security Architecture

| Concern | Implementation |
|---------|----------------|
| API keys | Never in browser code; read from `.env` server-side only |
| Portfolio data | Stored in local SQLite only; never sent to AI providers |
| Secrets in git | `.gitignore` excludes `.env`, `*.db`, portfolio CSVs |
| Data leaving machine | Only RSS fetch URLs; listed explicitly in Methodology screen |
| AI-generated content | Always labeled `model_interpretation`, never `verified_fact` |
| Synthetic demo data | Prominently labeled `[DEMO / SYNTHETIC DATA]` on every screen |

---

## 10. Test Coverage

```mermaid
pie title 46 pytest tests
    "Scenario Engine (30)" : 30
    "RSS Ingestion (16)" : 16
```

**Scenario engine tests cover:**
- `validate_scenario_probabilities` — edge cases, sum tolerance
- `calculate_portfolio_return` — weight validation, weighted sum
- `calculate_expected_return` — multi-scenario weighting
- `apply_stress_shocks` — sector sensitivities, P&L calculation
- `run_monte_carlo` — reproducibility (seed=42), percentile ordering, VaR

**RSS ingestion tests cover:**
- `compute_fingerprint` — consistency, URL normalization
- `apply_topic_tags` — French/English keyword detection, bilingual
- `detect_duplicates_in_batch` — exact match, case sensitivity

---

## 11. File Structure

```
france-political-intelligence/
├── backend/
│   ├── main.py                    # FastAPI app + lifespan
│   ├── database.py                # SQLAlchemy engine + session
│   ├── models.py                  # 16 SQLAlchemy models
│   ├── seed_data.py               # Demo data (40 CAC40, 4 scenarios, portfolio)
│   ├── requirements.txt
│   ├── routers/
│   │   ├── health.py
│   │   ├── news.py
│   │   ├── scenarios.py
│   │   ├── companies.py
│   │   ├── portfolio.py
│   │   ├── stress_tests.py
│   │   ├── ecb.py
│   │   └── methodology.py
│   ├── services/
│   │   ├── scenario_engine.py     # Pure deterministic functions
│   │   ├── rss_ingestion.py       # Async feed fetcher + dedup
│   │   └── ai_adapter.py          # Provider-neutral AI abstraction
│   └── tests/
│       ├── test_scenario_engine.py  # 30 tests
│       └── test_rss_ingestion.py    # 16 tests
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx          # Root layout (Sidebar + Inter)
│   │   │   ├── page.tsx            # Overview
│   │   │   ├── news/page.tsx       # News Intelligence
│   │   │   ├── scenarios/page.tsx  # Political Scenarios
│   │   │   ├── companies/page.tsx  # CAC 40 Universe
│   │   │   ├── portfolio/page.tsx  # Portfolio + CSV import
│   │   │   ├── stress-test/page.tsx# Stress Testing
│   │   │   ├── ecb/page.tsx        # ECB Module
│   │   │   └── methodology/page.tsx# Methodology & Audit
│   │   ├── components/
│   │   │   ├── layout/Sidebar.tsx
│   │   │   ├── layout/Header.tsx
│   │   │   ├── ui/DemoLabel.tsx
│   │   │   └── ui/InfoTypeLabel.tsx
│   │   └── lib/
│   │       ├── api.ts              # Fetch client
│   │       └── types.ts            # TypeScript interfaces
│   └── package.json
├── data/
│   ├── rss_sources.yaml           # 17 configured feed URLs
│   └── france_intel.db            # Auto-created SQLite (gitignored)
├── mcp_server.py                  # Optional local MCP (12 tools)
├── start.sh                       # One-command startup
├── .env.example
└── .gitignore
```

---

## 12. Production Roadmap

```mermaid
gantt
    title Production Roadmap
    dateFormat  YYYY-MM
    section Infrastructure
    PostgreSQL migration          :2027-01, 1M
    Docker + docker-compose       :2027-01, 1M
    Redis cache for feeds         :2027-02, 1M
    section Security
    Auth (NextAuth.js + OAuth)    :2027-02, 2M
    Row-level encryption for holdings :2027-03, 1M
    Audit log API                 :2027-03, 1M
    section Data
    Live RSS scheduler (APScheduler) :2027-02, 1M
    Real broker portfolio import  :2027-03, 2M
    Historical CAC40 price feed   :2027-04, 2M
    section AI
    RAG over ingested articles    :2027-04, 2M
    Citation tracing pipeline     :2027-05, 2M
    section UX
    Mobile-responsive layout      :2027-04, 1M
    Export to PDF/Excel           :2027-05, 1M
```

### Key gaps vs. production

| Area | MVP | Production |
|------|-----|-----------|
| Database | SQLite (local) | PostgreSQL (server) |
| Auth | None | OAuth2 + JWT |
| Portfolio import | CSV upload | Broker API / IBKR |
| RSS scheduling | Manual trigger | APScheduler (hourly) |
| AI analysis | Deterministic fallback | Full RAG pipeline |
| CAC40 prices | Synthetic seed data | Live market data feed |
| Scenario calibration | Manual probability sliders | Bayesian update on news |
| Deployment | localhost | Docker + reverse proxy |
| Monitoring | None | Prometheus + Grafana |
| Backup | None | Automated DB backups |

---

## 13. Data Leaving the Machine

The following **and only the following** data leaves localhost in this MVP:

| What | Where | When |
|------|-------|------|
| HTTP GET to RSS feed URLs | 17 configured external sources | On manual "Refresh Feeds" trigger |
| HTTP POST to AI provider API | Gemini / Groq / OpenRouter (if configured) | On article analysis, when `AI_PROVIDER ≠ none` |

**What never leaves:**
- Portfolio holdings, weights, or values
- User-uploaded CSV files
- SQLite database contents
- Any personal data

---

## 14. Known Limitations (MVP)

1. **No authentication** — anyone with localhost:3000 access can read all data
2. **Synthetic market data** — CAC40 exposures and prices are illustrative, not live
3. **RSS fetch is manual** — no background scheduler; must click "Refresh Feeds"
4. **Scenario probabilities are user-set** — not calibrated against prediction markets or news
5. **Monte Carlo uses diagonal covariance** — no correlation matrix between assets
6. **ECB candidate profiles are illustrative** — not authoritative analyst research
7. **AI analysis off by default** — `AI_PROVIDER=none` means all tagging is keyword-based
8. **No data export** — cannot export stress test results or portfolio analysis to PDF/Excel
