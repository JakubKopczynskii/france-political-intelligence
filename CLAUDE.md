# CLAUDE.md

Read `docs/ENGINEERING_HANDOFF.md` first: architecture, models, known issues (ranked) and roadmap (ranked by utility and shareability).

- Run: `bash start.sh`. Tests: `cd backend && python3 -m pytest -q`. Frontend checks: `cd frontend && npx tsc --noEmit && npx next lint`.
- Secrets only in `backend/.env`. Never stage `.env`, `data/`, `rough_notes*`. Scan `git diff --cached` for `ghp_|gsk_|sk-` before committing.
- Portfolio holdings must never be sent to any external service.
- CAC 40 constituents come only from `backend/cac40.py`.
- `political_scenarios.prior_probability` is immutable; only the daily job persists blended probabilities.
- To check UI without clicking: `/scenarios?tab=heatmap&method=historical` (also `replay`, `history`, `sentiment`).
