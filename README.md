# France Political Intelligence & CAC 40 Portfolio Scenario Simulator

> **Local MVP** — All scenario data is illustrative analyst input.  
> No live market data. No authentication. For research use only.

---

## Quick Start

```bash
# 1. Clone and enter the project
cd france-political-intelligence

# 2. Copy environment config
cp .env.example .env

# 3. Install Python dependencies
pip install -r backend/requirements.txt

# 4. Install Node.js dependencies
export PATH="/usr/local/lib/nodejs/node-v20.18.0-darwin-x64/bin:$PATH"
cd frontend && npm install && cd ..

# 5. Start both servers
./start.sh
```

Open **http://localhost:3000** in your browser.  
API docs: **http://localhost:8000/docs**

---

## Manual Start (if start.sh has issues)

**Terminal 1 — Backend:**
```bash
cd backend
python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

**Terminal 2 — Frontend:**
```bash
export PATH="/usr/local/lib/nodejs/node-v20.18.0-darwin-x64/bin:$PATH"
cd frontend
npm run dev
```

---

## Configuration

Edit `.env` (copied from `.env.example`):

```bash
# AI Provider — optional, default is deterministic keyword mode
AI_PROVIDER=none           # none | gemini | groq | openrouter

# Only needed if AI_PROVIDER is not "none"
GEMINI_API_KEY=
GROQ_API_KEY=
OPENROUTER_API_KEY=

BACKEND_PORT=8000
DATABASE_URL=sqlite:///./data/france_intel.db
```

**Security note:** `.env` is gitignored. Never commit API keys.

---

## Running Tests

```bash
cd backend
python3 -m pytest tests/ -v
```

Expected output: **46 passed** (30 scenario engine + 16 RSS ingestion).

---

## Application Screens

| Screen | URL | Description |
|--------|-----|-------------|
| Overview | `/` | Scenario probabilities, latest events, sector exposure |
| News Intelligence | `/news` | Article feed with topic filters, search, detail modal |
| Political Scenarios | `/scenarios` | 4 French political scenarios with policy detail |
| CAC 40 Universe | `/companies` | 40 companies, sector filter, exposure breakdown |
| Portfolio | `/portfolio` | Holdings, weights, CSV import |
| Stress Testing | `/stress-test` | Shock inputs, P&L results, Monte Carlo |
| ECB Module | `/ecb` | Lagarde succession scenarios with market impact |
| Methodology | `/methodology` | Information taxonomy, data sources, model audit |

---

## Political Scenarios

| Scenario | Probability | Description |
|----------|-------------|-------------|
| Centrist Coalition | 35% | Reform continuation, fiscal consolidation |
| NR-led Government | 25% | Nationalist policies, EU tensions |
| Left-wing Coalition (NFP) | 25% | Wealth taxes, wage increases |
| Hung Parliament | 15% | Legislative paralysis |

> These are illustrative analyst inputs — not predictions or investment recommendations.

---

## Data Sources

Configured RSS feeds in `data/rss_sources.yaml`:

- **Official:** Élysée, Gouvernement.fr, Assemblée Nationale, Sénat, Ministère de l'Économie
- **Institutional:** Banque de France, INSEE, ECB, Eurostat, AMF, European Commission
- **Press:** Le Monde, Les Echos, Le Figaro, Reuters, Financial Times, Euronews

Feeds are fetched on demand via the "Refresh Feeds" button — no background scheduler in MVP.

---

## MCP Server (optional)

Expose the backend as a local MCP server for Claude Code integration:

```bash
# Add to your Claude Code MCP config (~/.claude/settings.json):
{
  "mcpServers": {
    "france-intel": {
      "command": "python3",
      "args": ["/path/to/france-political-intelligence/mcp_server.py"]
    }
  }
}
```

12 read-only tools: `get_latest_news`, `get_political_scenarios`, `run_stress_test`, etc.  
Requires backend running at `http://localhost:8000`.

---

## Deleting Local Data

```bash
# Reset demo data (keeps tables, re-seeds):
curl -X POST http://localhost:8000/api/admin/reset-demo

# Delete the entire database:
rm data/france_intel.db
# It will be re-created with demo data on next backend start.

# Remove imported portfolio CSV files:
rm data/portfolio_imports/*.csv  # if any exist
```

---

## Architecture

See [`docs/MVP_ARCHITECTURE_AND_NEXT_STEPS.md`](docs/MVP_ARCHITECTURE_AND_NEXT_STEPS.md) for:
- Full system architecture with Mermaid diagrams
- Data flow for RSS ingestion and stress testing
- Entity-relationship diagram
- Security architecture
- Production roadmap

---

## Limitations

- **No live market data** — all prices and exposures are synthetic
- **No authentication** — localhost only, no user accounts
- **RSS scheduling is manual** — click "Refresh Feeds" to ingest
- **AI analysis is off by default** — set `AI_PROVIDER` to enable
- **Scenario probabilities are user-set** — not market-calibrated

---

## Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI + Python 3.10+ |
| Database | SQLAlchemy + SQLite (PostgreSQL-ready) |
| Frontend | Next.js 14 + React 18 + TypeScript |
| Styling | Tailwind CSS (dark theme) |
| Charts | Recharts |
| Icons | lucide-react |
| Testing | pytest (46 tests) |
