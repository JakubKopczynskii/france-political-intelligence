"""
2027 presidential election model.

Data: French Wikipedia "Liste de sondages sur l'élection présidentielle française de 2027"
(CC BY-SA). Only published poll percentages are used.

Method:
  1. Parse every first-round poll hypothesis (each poll tests several candidate line-ups)
     and every second-round head-to-head table.
  2. Monte Carlo: each draw picks a recent first-round hypothesis (recency-weighted,
     one unit of weight per poll split across its hypotheses), adds polling error,
     sends the top two to a runoff, and resolves the runoff from head-to-head poll
     averages plus polling error.
  3. Aggregate: P(reach runoff), P(win), likely runoffs, win probability by political bloc.
"""
from __future__ import annotations
import math
import random
import re
import unicodedata
import urllib.request
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone

SOURCE_URL = "https://fr.wikipedia.org/wiki/Liste_de_sondages_sur_l%27%C3%A9lection_pr%C3%A9sidentielle_fran%C3%A7aise_de_2027"
FIRST_ROUND = date(2027, 4, 18)
SECOND_ROUND = date(2027, 5, 2)

N_SIMS = 20000
R1_WINDOW_DAYS = 45
R2_WINDOW_DAYS = 120
RECENCY_HALF_LIFE_DAYS = 21

_MONTHS = {
    "janvier": 1, "février": 2, "fevrier": 2, "mars": 3, "avril": 4, "mai": 5, "juin": 6,
    "juillet": 7, "août": 8, "aout": 8, "septembre": 9, "octobre": 10, "novembre": 11,
    "décembre": 12, "decembre": 12,
}

_PARTY_BLOC = {
    "LO": "left", "NPA": "left", "LFI": "left", "PCF": "left", "LE": "left", "EELV": "left",
    "PS": "left", "PP": "left", "GRS": "left", "DVG": "left", "APRES": "left", "DEBOUT": "left",
    "G.S": "left", "GS": "left",
    "RE": "centre_right", "EPR": "centre_right", "HOR": "centre_right", "MODEM": "centre_right",
    "MD": "centre_right", "LR": "centre_right", "NE": "centre_right", "UDI": "centre_right",
    "DVD": "centre_right", "DVC": "centre_right",
    "REN": "centre_right", "ENS": "centre_right",
    "RN": "far_right", "REC": "far_right", "DLF": "far_right", "UDR": "far_right", "LP": "far_right",
}

BLOC_TO_SCENARIO = {"far_right": "national_rally", "left": "left_wing", "centre_right": "centrist"}
BLOC_LABEL = {"far_right": "Far right", "centre_right": "Centre & right", "left": "Left", "other": "Other"}

_NAME_BLOC = {"ruffin": "left", "macron": "centre_right"}

# Le Pen and Bardella are polled as alternative RN candidates.
_RN_ALIASES = {"le pen", "bardella", "candidat rn"}
RN_SERIES_KEY = "rn"


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", s).strip().lower()


def _clean(text: str) -> str:
    return re.sub(r"\[\s*[^\]]*\]", "", text).replace("\xa0", " ").strip()


def _num(text: str) -> float | None:
    m = re.match(r"^\s*(\d+(?:[.,]\d+)?)", _clean(text))
    return float(m.group(1).replace(",", ".")) if m else None


def _parse_date(text: str, default_year: int | None) -> date | None:
    text = _norm(_clean(text)).replace("1er", "1")
    hits = list(re.finditer(r"(\d{1,2})\s+([a-z]+)\.?(?:\s+(\d{4}))?", text))
    for m in reversed(hits):
        month = _MONTHS.get(m.group(2)) or next((v for k, v in _MONTHS.items() if _norm(k).startswith(m.group(2)[:4])), None)
        if not month:
            continue
        year = int(m.group(3)) if m.group(3) else default_year
        if not year:
            return None
        try:
            return date(year, month, int(m.group(1)))
        except ValueError:
            return None
    return None


def _grid(table) -> list[list]:
    cells: dict[tuple[int, int], object] = {}
    rows = table.find_all("tr")
    for r, tr in enumerate(rows):
        c = 0
        for cell in tr.find_all(["th", "td"], recursive=False):
            while (r, c) in cells:
                c += 1
            rs = int(re.sub(r"\D", "", str(cell.get("rowspan", "1"))) or 1)
            cs = int(re.sub(r"\D", "", str(cell.get("colspan", "1"))) or 1)
            for dr in range(rs):
                for dc in range(cs):
                    cells[(r + dr, c + dc)] = cell
            c += cs
    if not cells:
        return []
    ncols = max(c for _, c in cells) + 1
    return [[cells.get((r, c)) for c in range(ncols)] for r in range(len(rows))]


def _candidate_from_header(cell) -> dict | None:
    if cell is None or cell.name != "th":
        return None
    link = next((a for a in cell.find_all("a") if a.get("title") and not a.get("href", "").startswith("#")), None)
    text = _clean(cell.get_text(" ", strip=True))
    if not link or not text:
        return None
    name = text.split("(")[0].strip()
    party_m = re.search(r"\(\s*([^)]+?)\s*\)", text)
    party = party_m.group(1).replace(" ", "") if party_m else ""
    bloc = _NAME_BLOC.get(_norm(name)) or bloc_for(party or name.replace("Candidat", ""))
    return {"key": _norm(name), "name": name, "full_name": link["title"], "party": party, "bloc": bloc}


def bloc_for(party: str) -> str:
    for token in re.split(r"[^A-Za-z.]+", party.upper()):
        if token in _PARTY_BLOC:
            return _PARTY_BLOC[token]
    return "other"


def _header(grid) -> tuple[int, dict[int, dict]] | None:
    for r, row in enumerate(grid[:6]):
        cols: dict[int, dict] = {}
        seen = set()
        for c, cell in enumerate(row):
            if cell is None or id(cell) in seen:
                continue
            seen.add(id(cell))
            cand = _candidate_from_header(cell)
            if cand:
                cols[c] = cand
        if len(cols) >= 2:
            return r, cols
    return None


def _heading_text(el, tag: str) -> str:
    h = el.find_previous(tag)
    return h.get_text(" ", strip=True) if h else ""


def parse_polls(html: str) -> dict:
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "lxml")
    first_round: list[dict] = []
    second_round: list[dict] = []
    candidates: dict[str, dict] = {}

    for table in soup.select("table.wikitable"):
        section = _norm(_heading_text(table, "h2"))
        grid = _grid(table)
        hdr = _header(grid)
        if not hdr:
            continue
        hrow, cols = hdr
        for cand in cols.values():
            candidates.setdefault(cand["key"], cand)

        if "premier tour" in section:
            year_m = re.search(r"(20\d\d)", _heading_text(table, "h3"))
            default_year = int(year_m.group(1)) if year_m else None
            polls: dict[tuple, dict] = {}
            for row in grid[hrow + 1:]:
                if not row[0] or not row[1]:
                    continue
                values = {}
                for c, cand in cols.items():
                    if c < len(row) and row[c] is not None:
                        v = _num(row[c].get_text(" ", strip=True))
                        if v is not None:
                            values[cand["key"]] = v
                if len(values) < 2:
                    continue
                d = _parse_date(row[1].get_text(" ", strip=True), default_year)
                if not d:
                    continue
                pid = (id(row[0]), id(row[1]))
                poll = polls.setdefault(pid, {
                    "pollster": _clean(row[0].get_text(" ", strip=True)), "date": d, "hypotheses": [],
                })
                poll["hypotheses"].append(values)
            first_round.extend(polls.values())

        elif "second tour" in section and len(cols) == 2:
            (ca, a), (cb, b) = sorted(cols.items())
            for row in grid[hrow + 1:]:
                if not row[0] or not row[1] or max(ca, cb) >= len(row):
                    continue
                va = _num(row[ca].get_text(" ", strip=True)) if row[ca] else None
                vb = _num(row[cb].get_text(" ", strip=True)) if row[cb] else None
                d = _parse_date(row[1].get_text(" ", strip=True), None)
                if va is None or vb is None or not d or va + vb <= 0:
                    continue
                second_round.append({
                    "a": a["key"], "b": b["key"], "a_share": 100 * va / (va + vb),
                    "date": d, "pollster": _clean(row[0].get_text(" ", strip=True)),
                })

    return {"first_round": first_round, "second_round": second_round, "candidates": candidates}


def fetch_html() -> str:
    req = urllib.request.Request(SOURCE_URL, headers={"User-Agent": "france-political-intelligence/0.1 (local research tool)"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8")


class _RunoffTable:
    def __init__(self, polls: list[dict], newest: date, cands: dict[str, dict]):
        self.cands = cands
        by_pair: dict[frozenset, list[dict]] = defaultdict(list)
        for p in polls:
            by_pair[frozenset((p["a"], p["b"]))].append(p)
        self.pairs: dict[frozenset, dict] = {}
        for pair, ps in by_pair.items():
            ps.sort(key=lambda p: p["date"], reverse=True)
            recent = [p for p in ps if (newest - p["date"]).days <= R2_WINDOW_DAYS] or ps[:3]
            ref = recent[0]["a"]
            shares = [p["a_share"] if p["a"] == ref else 100 - p["a_share"] for p in recent]
            self.pairs[pair] = {
                "ref": ref, "share": sum(shares) / len(shares), "n": len(recent),
                "latest": recent[0]["date"].isoformat(), "stale": (newest - recent[0]["date"]).days > R2_WINDOW_DAYS,
            }

    def _lookup(self, a: str, b: str) -> float | None:
        rec = self.pairs.get(frozenset((a, b)))
        if not rec:
            return None
        return rec["share"] if rec["ref"] == a else 100 - rec["share"]

    def _direct(self, a: str, b: str) -> float | None:
        exact = self._lookup(a, b)
        if exact is not None:
            return exact
        a_alts = sorted(_RN_ALIASES - {a}) if a in _RN_ALIASES else [a]
        b_alts = sorted(_RN_ALIASES - {b}) if b in _RN_ALIASES else [b]
        for x in a_alts:
            for y in b_alts:
                v = self._lookup(x, y)
                if v is not None:
                    return v
        return None

    def _vs_rn(self, k: str) -> float | None:
        """k's runoff share against the RN candidate; falls back to the average of k's political bloc."""
        if k in _RN_ALIASES:
            return None
        direct = self._direct(k, "le pen")
        if direct is not None:
            return direct
        bloc = self.cands.get(k, {}).get("bloc")
        peers = [v for c, v in ((c, self._direct(c, "le pen")) for c, info in self.cands.items()
                                if info.get("bloc") == bloc and c != k and c not in _RN_ALIASES) if v is not None]
        return sum(peers) / len(peers) if peers else None

    def share(self, a: str, b: str) -> tuple[float, bool]:
        """a's expected runoff share vs b, and whether it is estimated rather than polled."""
        direct = self._direct(a, b)
        if direct is not None:
            return direct, False
        if b in _RN_ALIASES and (v := self._vs_rn(a)) is not None:
            return v, True
        if a in _RN_ALIASES and (v := self._vs_rn(b)) is not None:
            return 100 - v, True
        a_rn, b_rn = self._vs_rn(a), self._vs_rn(b)
        if a_rn is not None and b_rn is not None:
            return 50 + (a_rn - b_rn) / 2, True
        return 50.0, True


def _weighted_hypotheses(first_round: list[dict]) -> tuple[list[dict], list[float], date, date]:
    newest = max(p["date"] for p in first_round)
    window = R1_WINDOW_DAYS
    recent = [p for p in first_round if (newest - p["date"]).days <= window]
    while len(recent) < 4 and window < 365:
        window *= 2
        recent = [p for p in first_round if (newest - p["date"]).days <= window]
    hyps, weights = [], []
    for p in recent:
        w = 0.5 ** ((newest - p["date"]).days / RECENCY_HALF_LIFE_DAYS) / len(p["hypotheses"])
        for h in p["hypotheses"]:
            hyps.append(h)
            weights.append(w)
    oldest = min(p["date"] for p in recent)
    return hyps, weights, oldest, newest


def poll_history(first_round: list[dict], keys: list[str], since: date, step_days: int = 14, window_days: int = 30) -> dict:
    dates, series = [], {k: [] for k in keys}
    newest = max(p["date"] for p in first_round)
    d = since
    while d <= newest:
        window = [p for p in first_round if 0 <= (d - p["date"]).days < window_days]
        if len(window) >= 2:
            dates.append(d.isoformat())
            for k in keys:
                vals = []
                for p in window:
                    if k == RN_SERIES_KEY:
                        pv = [next(h[a] for a in _RN_ALIASES if a in h) for h in p["hypotheses"] if _RN_ALIASES & h.keys()]
                    else:
                        pv = [h[k] for h in p["hypotheses"] if k in h]
                    if pv:
                        vals.append(sum(pv) / len(pv))
                series[k].append(round(sum(vals) / len(vals), 1) if vals else None)
        d += timedelta(days=step_days)
    return {"dates": dates, "series": series}


def simulate(parsed: dict, today: date | None = None, n_sims: int = N_SIMS, seed: int = 2027) -> dict:
    today = today or date.today()
    first_round = parsed["first_round"]
    if not first_round:
        raise ValueError("No first-round polls parsed")
    cands = parsed["candidates"]
    hyps, weights, oldest, newest = _weighted_hypotheses(first_round)
    newest_r2 = max((p["date"] for p in parsed["second_round"]), default=newest)
    runoffs = _RunoffTable(parsed["second_round"], newest_r2, cands)

    days_out = max(0, (FIRST_ROUND - today).days)
    time_factor = 1 + min(days_out, 365) / 365
    r2_sigma = 4.0 * time_factor

    rng = random.Random(seed)
    reach = defaultdict(int)
    wins = defaultdict(int)
    matchups = defaultdict(lambda: {"n": 0, "wins": defaultdict(int)})
    bloc_wins = defaultdict(int)
    runoff_cache: dict[tuple, tuple[float, bool]] = {}

    for _ in range(n_sims):
        h = rng.choices(hyps, weights=weights, k=1)[0]
        drawn = sorted(
            ((k, v + rng.gauss(0, time_factor * (1.5 + 0.1 * v))) for k, v in h.items()),
            key=lambda kv: kv[1], reverse=True,
        )
        a, b = drawn[0][0], drawn[1][0]
        reach[a] += 1
        reach[b] += 1
        pair = (a, b) if a < b else (b, a)
        if pair not in runoff_cache:
            runoff_cache[pair] = runoffs.share(pair[0], pair[1])
        share, estimated = runoff_cache[pair]
        sigma = r2_sigma + (4.0 if estimated else 0.0)
        winner = pair[0] if share + rng.gauss(0, sigma) > 50 else pair[1]
        wins[winner] += 1
        matchups[pair]["n"] += 1
        matchups[pair]["wins"][winner] += 1
        bloc_wins[cands.get(winner, {}).get("bloc", "other")] += 1

    # Poll averages across the same recent window (unweighted mean of hypotheses that include the candidate)
    sums, counts, mins, maxs = defaultdict(float), defaultdict(int), {}, {}
    for h in hyps:
        for k, v in h.items():
            sums[k] += v
            counts[k] += 1
            mins[k] = min(mins.get(k, v), v)
            maxs[k] = max(maxs.get(k, v), v)

    candidates_out = []
    for k in counts:
        c = cands.get(k, {"name": k, "full_name": k, "party": "", "bloc": "other"})
        candidates_out.append({
            "key": k, "name": c["name"], "full_name": c["full_name"], "party": c["party"],
            "bloc": c["bloc"], "bloc_label": BLOC_LABEL[c["bloc"]],
            "poll_avg": round(sums[k] / counts[k], 1), "poll_min": mins[k], "poll_max": maxs[k],
            "hypotheses_tested": counts[k], "hypotheses_share": round(counts[k] / len(hyps), 3),
            "p_runoff": round(reach[k] / n_sims, 4), "p_win": round(wins[k] / n_sims, 4),
        })
    candidates_out.sort(key=lambda c: (c["p_win"], c["poll_avg"]), reverse=True)

    matchups_out = []
    for (a, b), m in sorted(matchups.items(), key=lambda kv: kv[1]["n"], reverse=True)[:10]:
        share, estimated = runoff_cache[(a, b)]
        matchups_out.append({
            "a": cands.get(a, {}).get("name", a), "b": cands.get(b, {}).get("name", b),
            "a_key": a, "b_key": b,
            "probability": round(m["n"] / n_sims, 4),
            "a_poll_share": round(share, 1), "estimated": estimated,
            "a_win_prob": round(m["wins"][a] / m["n"], 3),
        })

    blocs = {b: round(bloc_wins[b] / n_sims, 4) for b in ("far_right", "centre_right", "left", "other")}
    mapped = {BLOC_TO_SCENARIO[b]: blocs[b] for b in BLOC_TO_SCENARIO}
    total = sum(mapped.values()) or 1.0
    scenario_signal = {k: round(v / total, 4) for k, v in mapped.items()}

    top_keys = [c["key"] for c in sorted(candidates_out, key=lambda c: c["poll_avg"], reverse=True)[:8]]
    # One RN line across periods polled as "Candidat RN", Bardella or Le Pen
    if any(k in _RN_ALIASES for k in top_keys):
        top_keys = [RN_SERIES_KEY] + [k for k in top_keys if k not in _RN_ALIASES]
    history = poll_history(first_round, top_keys, since=max(min(p["date"] for p in first_round), date(2025, 1, 1)))
    history["names"] = {k: "RN candidate" if k == RN_SERIES_KEY else cands.get(k, {}).get("name", k) for k in top_keys}

    runoff_polls = [
        {"a": cands.get(r["ref"], {}).get("name", r["ref"]),
         "b": cands.get(next(iter(pair - {r["ref"]})), {}).get("name", "?"),
         "a_share": round(r["share"], 1), "n": r["n"], "latest": r["latest"], "stale": r["stale"]}
        for pair, r in runoffs.pairs.items()
    ]
    runoff_polls.sort(key=lambda r: r["latest"], reverse=True)

    return {
        "source_url": SOURCE_URL,
        "computed_at": datetime.now(timezone.utc).isoformat(),
        "first_round_date": FIRST_ROUND.isoformat(),
        "second_round_date": SECOND_ROUND.isoformat(),
        "days_to_first_round": days_out,
        "window": {"from": oldest.isoformat(), "to": newest.isoformat(),
                   "n_polls": sum(1 for p in first_round if oldest <= p["date"] <= newest),
                   "n_hypotheses": len(hyps)},
        "n_first_round_polls_total": len(first_round),
        "n_second_round_polls_total": len(parsed["second_round"]),
        "n_sims": n_sims,
        "candidates": candidates_out,
        "matchups": matchups_out,
        "blocs": blocs,
        "bloc_labels": BLOC_LABEL,
        "scenario_signal": scenario_signal,
        "runoff_polls": runoff_polls,
        "history": history,
        "assumptions": {
            "first_round_error_pts": f"{time_factor:.2f} × (1.5 + 0.1 × share) — e.g. ±{time_factor * 4.5:.1f} pts at 30%",
            "second_round_error_pts": f"{r2_sigma:.1f} (+4 when no head-to-head poll exists)",
            "time_factor": round(time_factor, 2),
            "recency_half_life_days": RECENCY_HALF_LIFE_DAYS,
            "first_round_window_days": R1_WINDOW_DAYS,
            "rn_candidate": "Le Pen and Bardella are polled as alternative RN candidates; head-to-heads are shared between them when one is missing",
            "missing_head_to_head": "Estimated from each candidate's polled score against the RN candidate",
        },
    }


def run() -> dict:
    return simulate(parse_polls(fetch_html()))
