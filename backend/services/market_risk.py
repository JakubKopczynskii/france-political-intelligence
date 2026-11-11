"""
Market-implied French political risk gauge.

Components (higher percentile = more stress):
  1. OAT–Bund 10y spread (bp) — ECB long-term interest rate statistics (monthly).
  2. CAC40 vs DAX, 20-trading-day relative return — French equities vs German.
  3. French banks (BNP, SocGen, Crédit Agricole) vs STOXX Europe 600 Banks ETF, 20-day relative return.

Each component is ranked against its own history (spread: 5 years; equities: 3 years).
Composite = average percentile. The June 2024 dissolution is shown as a reference point.
Only public index/ticker identifiers are sent to Yahoo Finance and the ECB.
"""
from __future__ import annotations
import csv
import io
import urllib.request
from datetime import date, datetime, timedelta, timezone

ECB_URL = "https://data-api.ecb.europa.eu/service/data/IRS/M.{cc}.L.L40.CI.0000.EUR.N.Z?format=csvdata&startPeriod={start}"
FR_BANKS = ["BNP.PA", "GLE.PA", "ACA.PA"]
EU_BANKS = "EXV1.DE"
WINDOW = 20
REFERENCE_DATE = "2024-06-14"
REFERENCE_MONTH = "2024-06"


def _ecb_series(cc: str, start: str) -> dict[str, float]:
    req = urllib.request.Request(ECB_URL.format(cc=cc, start=start), headers={"User-Agent": "france-political-intelligence/0.1"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        rows = csv.DictReader(io.StringIO(resp.read().decode("utf-8")))
        return {r["TIME_PERIOD"]: float(r["OBS_VALUE"]) for r in rows if r.get("OBS_VALUE")}


def _percentile(history: list[float], value: float) -> float:
    if not history:
        return 50.0
    return round(100 * sum(1 for h in history if h <= value) / len(history), 1)


def _compute_sync() -> dict:
    import yfinance as yf

    start_month = f"{date.today().year - 5}-01"
    fr, de = _ecb_series("FR", start_month), _ecb_series("DE", start_month)
    months = sorted(set(fr) & set(de))
    spread = [(m, round((fr[m] - de[m]) * 100, 1)) for m in months]

    closes = yf.download(["^FCHI", "^GDAXI", EU_BANKS] + FR_BANKS,
                         start=(date.today() - timedelta(days=3 * 365 + 40)).isoformat(),
                         end=(date.today() + timedelta(days=1)).isoformat(),
                         auto_adjust=True, progress=False)["Close"].ffill().dropna()
    rel_index = (closes["^FCHI"].pct_change(WINDOW) - closes["^GDAXI"].pct_change(WINDOW)) * 100
    fr_basket = closes[FR_BANKS].div(closes[FR_BANKS].iloc[0]).mean(axis=1)
    rel_banks = (fr_basket.pct_change(WINDOW) - closes[EU_BANKS].pct_change(WINDOW)) * 100
    rel_index, rel_banks = rel_index.dropna(), rel_banks.dropna()

    def daily_component(series, cid, label, description):
        hist = [-v for v in series.tolist()]
        current = float(series.iloc[-1])
        ref = series.loc[:REFERENCE_DATE]
        ref_val = float(ref.iloc[-1]) if len(ref) else None
        weekly = series.iloc[::5]
        return {
            "id": cid, "label": label, "unit": "%", "description": description,
            "value": round(current, 2), "as_of": series.index[-1].date().isoformat(),
            "percentile": _percentile(hist, -current),
            "reference_value": round(ref_val, 2) if ref_val is not None else None,
            "reference_percentile": _percentile(hist, -ref_val) if ref_val is not None else None,
            "worst_value": round(float(series.min()), 2), "worst_date": series.idxmin().date().isoformat(),
            "series": [{"date": d.date().isoformat(), "value": round(float(v), 2)} for d, v in weekly.items()],
            "source": "Yahoo Finance",
        }

    spread_vals = [v for _, v in spread]
    ref_spread = dict(spread).get(REFERENCE_MONTH)
    spread_component = {
        "id": "oat_bund_spread", "label": "OAT–Bund 10y spread", "unit": "bp",
        "description": "French minus German 10-year government bond yield (monthly average). Widens when investors demand more to hold French debt.",
        "value": spread[-1][1], "as_of": spread[-1][0],
        "percentile": _percentile(spread_vals, spread[-1][1]),
        "reference_value": ref_spread,
        "reference_percentile": _percentile(spread_vals, ref_spread) if ref_spread is not None else None,
        "worst_value": max(spread_vals), "worst_date": max(spread, key=lambda x: x[1])[0],
        "series": [{"date": m, "value": v} for m, v in spread],
        "source": "ECB Data Portal (IRS)",
    }

    components = [
        spread_component,
        daily_component(rel_index, "cac_vs_dax", "CAC40 vs DAX (20d)",
                        "CAC40 return minus DAX return over the last 20 trading days. Negative = French equities lagging German ones."),
        daily_component(rel_banks, "fr_banks_vs_eu", "French banks vs EU banks (20d)",
                        "BNP/SocGen/Crédit Agricole basket minus STOXX Europe 600 Banks over 20 trading days. French banks hold large amounts of French government debt."),
    ]
    score = round(sum(c["percentile"] for c in components) / len(components), 1)
    ref_scores = [c["reference_percentile"] for c in components if c["reference_percentile"] is not None]
    ref_score = round(sum(ref_scores) / len(ref_scores), 1) if ref_scores else None

    if score >= 80:
        label = "High stress"
    elif score >= 60:
        label = "Elevated"
    elif score >= 40:
        label = "Normal"
    else:
        label = "Calm"

    return {
        "computed_at": datetime.now(timezone.utc).isoformat(),
        "composite": {"score": score, "label": label, "reference_score": ref_score,
                      "reference_label": "June 2024 dissolution"},
        "components": components,
        "method": "Each component is ranked against its own history (spread 5y monthly, equities 3y daily); composite is the average percentile. 100 = most stressed reading in the sample.",
    }


async def compute() -> dict:
    import asyncio
    return await asyncio.to_thread(_compute_sync)
