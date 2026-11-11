"""
Event study of real French political shocks, used to calibrate scenario impacts.

For each episode we measure, per CAC40 stock:
  raw      = close(end) / close(start) - 1
  abnormal = raw - beta × DAX return over the same window
beta is estimated from 250 trading days of daily returns before the episode, so
the abnormal return strips out moves shared with German (non-French) equities.

Scenario impacts ("historical analog" method) = scale × weighted average of the
abnormal returns in that scenario's analog episodes. Episode choice, weights and
scales are explicit analyst assumptions listed in ANALOGS.
"""
from __future__ import annotations
from datetime import date, datetime, timedelta, timezone

from cac40 import CAC40, TICKERS

BENCHMARK = "^GDAXI"
INDEX = "^FCHI"
EU_BANKS = "EXV1.DE"

EPISODES = [
    {"id": "2017_r1", "label": "2017 presidential, 1st round", "start": "2017-04-21", "end": "2017-04-24",
     "description": "Macron and Le Pen qualify; Mélenchon eliminated. Relief rally on reduced euro-exit risk."},
    {"id": "2022_r2", "label": "2022 presidential, 2nd round", "start": "2022-04-22", "end": "2022-04-25",
     "description": "Macron re-elected against Le Pen (58.5%). Global markets fell the same day."},
    {"id": "2024_dissolution", "label": "June 2024 dissolution", "start": "2024-06-07", "end": "2024-06-14",
     "description": "Macron dissolves the Assemblée after the European elections; markets price an RN or NFP majority."},
    {"id": "2024_leg_r1", "label": "2024 legislative, 1st round", "start": "2024-06-28", "end": "2024-07-01",
     "description": "RN leads but an absolute majority looks less likely than feared."},
    {"id": "2024_leg_r2", "label": "2024 legislative, 2nd round", "start": "2024-07-05", "end": "2024-07-08",
     "description": "NFP comes first; no bloc has a majority."},
    {"id": "2024_barnier", "label": "Barnier government censured", "start": "2024-11-29", "end": "2024-12-05",
     "description": "First successful censure motion since 1962 brings down the Barnier government over the budget."},
    {"id": "2025_bayrou", "label": "Bayrou confidence vote called", "start": "2025-08-22", "end": "2025-08-29",
     "description": "Bayrou announces a confidence vote he is expected to lose; French banks sell off."},
    {"id": "2025_lecornu", "label": "Lecornu resigns", "start": "2025-10-03", "end": "2025-10-06",
     "description": "Prime Minister Lecornu resigns hours after naming his government."},
]

ANALOGS = {
    "centrist": {
        "episodes": {"2017_r1": 0.5, "2022_r2": 0.5}, "scale": 1.0, "confidence": "medium",
        "rationale": "Past centrist presidential wins. 2017 captures relief from a priced-in tail risk; 2022 a largely expected outcome.",
    },
    "national_rally": {
        "episodes": {"2024_dissolution": 1.0}, "scale": 1.5, "confidence": "medium",
        "rationale": "June 2024 priced only a partial probability of an RN majority; scaled ×1.5 for the outcome actually happening.",
    },
    "left_wing": {
        "episodes": {"2024_dissolution": 0.6, "2024_leg_r2": 0.4}, "scale": 1.5, "confidence": "low",
        "rationale": "No left-wing majority has occurred in the sample. Uses the dissolution sell-off (NFP risk was part of it) and the NFP first-place result, scaled ×1.5.",
    },
    "hung_parliament": {
        "episodes": {"2024_barnier": 0.25, "2025_bayrou": 0.35, "2025_lecornu": 0.25, "2024_leg_r2": 0.15}, "scale": 1.0, "confidence": "medium",
        "rationale": "Repeated government collapses under a parliament with no majority — the closest real analog.",
    },
}


def _compute_sync() -> dict:
    import numpy as np
    import yfinance as yf

    start = (date.fromisoformat(min(e["start"] for e in EPISODES)) - timedelta(days=420)).isoformat()
    symbols = TICKERS + [INDEX, BENCHMARK, EU_BANKS]
    closes = yf.download(symbols, start=start, end=date.today().isoformat(), auto_adjust=True, progress=False)["Close"]
    rets = closes.pct_change(fill_method=None)

    episodes_out = []
    for ep in EPISODES:
        window = closes.loc[ep["start"]:ep["end"]]
        if len(window) < 2:
            continue
        first, last = window.index[0], window.index[-1]
        pre = rets.loc[:first].iloc[-251:-1]
        bench_ret = float(window[BENCHMARK].iloc[-1] / window[BENCHMARK].iloc[0] - 1)
        stocks = {}
        for sym in symbols:
            s = window[sym]
            if s.isna().iloc[0] or s.isna().iloc[-1]:
                continue
            raw = float(s.iloc[-1] / s.iloc[0] - 1)
            beta = 1.0
            if sym != BENCHMARK:
                pair = pre[[sym, BENCHMARK]].dropna()
                if len(pair) >= 120:
                    cov = np.cov(pair[sym].to_numpy(), pair[BENCHMARK].to_numpy())
                    if cov[1, 1] > 0:
                        beta = float(cov[0, 1] / cov[1, 1])
            stocks[sym] = {
                "raw_pct": round(raw * 100, 2),
                "abnormal_pct": round((raw - beta * bench_ret) * 100, 2),
                "beta": round(beta, 2),
            }
        episodes_out.append({
            **ep, "trading_start": first.date().isoformat(), "trading_end": last.date().isoformat(),
            "cac_pct": stocks.get(INDEX, {}).get("raw_pct"),
            "dax_pct": round(bench_ret * 100, 2),
            "eu_banks_pct": stocks.get(EU_BANKS, {}).get("raw_pct"),
            "stocks": {k: v for k, v in stocks.items() if k in TICKERS},
            "index_abnormal_pct": stocks.get(INDEX, {}).get("abnormal_pct"),
        })

    return {"computed_at": datetime.now(timezone.utc).isoformat(), "episodes": episodes_out}


async def compute() -> dict:
    import asyncio
    return await asyncio.to_thread(_compute_sync)


def analog_impacts(cache: dict) -> dict[str, dict[str, dict]]:
    """{scenario: {ticker: {"impact_pct", "imputed"}}} from cached episode data."""
    eps = {e["id"]: e for e in cache.get("episodes", [])}
    out: dict[str, dict[str, dict]] = {}
    for slug, cfg in ANALOGS.items():
        out[slug] = {}
        for c in CAC40:
            t = c["ticker"]
            total_w, acc, imputed = 0.0, 0.0, False
            for ep_id, w in cfg["episodes"].items():
                ep = eps.get(ep_id)
                if not ep:
                    continue
                stock = ep["stocks"].get(t)
                if stock:
                    val = stock["abnormal_pct"]
                else:
                    peers = [ep["stocks"][p["ticker"]]["abnormal_pct"] for p in CAC40
                             if p["sector"] == c["sector"] and p["ticker"] in ep["stocks"]]
                    val = sum(peers) / len(peers) if peers else (ep.get("index_abnormal_pct") or 0.0)
                    imputed = True
                acc += w * val
                total_w += w
            if total_w:
                out[slug][t] = {"impact_pct": round(cfg["scale"] * acc / total_w, 2), "imputed": imputed}
    return out


def analogs_meta() -> dict:
    labels = {e["id"]: e["label"] for e in EPISODES}
    return {
        slug: {**cfg, "episode_labels": {k: labels[k] for k in cfg["episodes"]}}
        for slug, cfg in ANALOGS.items()
    }
