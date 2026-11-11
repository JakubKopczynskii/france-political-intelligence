"""
Wikipedia poll fetcher — scrapes French election polling aggregation pages.
Maps candidate/party support to our 4 scenario slugs.

No API key required. Data fetched from Wikipedia (CC BY-SA licensed).
Only polling percentages are stored — no personal data.
"""
from __future__ import annotations
import asyncio
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# --- Scenario mappings ---
# Maps Wikipedia column header keywords → scenario slug
_PARTY_TO_SCENARIO: dict[str, str] = {
    # Centrist / Macron-aligned
    "macron": "centrist",
    "renaissance": "centrist",
    "modem": "centrist",
    "horizons": "centrist",
    "ensemble": "centrist",
    "bayrou": "centrist",
    "centriste": "centrist",
    "liberal": "centrist",

    # National Rally
    "rassemblement national": "national_rally",
    "rn": "national_rally",
    "le pen": "national_rally",
    "bardella": "national_rally",
    "national rally": "national_rally",

    # Left wing
    "mélenchon": "left_wing",
    "melenchon": "left_wing",
    "lfi": "left_wing",
    "france insoumise": "left_wing",
    "nfp": "left_wing",
    "nouveau front populaire": "left_wing",
    "ps": "left_wing",
    "socialiste": "left_wing",
    "écologie": "left_wing",
    "greens": "left_wing",
    "lucie castets": "left_wing",
}

# Wikipedia pages to try (in order of relevance)
_WIKI_PAGES = [
    "https://en.wikipedia.org/wiki/Opinion_polling_for_the_2027_French_presidential_election",
    "https://fr.wikipedia.org/wiki/Sondages_sur_l%27%C3%A9lection_pr%C3%A9sidentielle_fran%C3%A7aise_de_2027",
    "https://en.wikipedia.org/wiki/2027_French_presidential_election",
]


def _parse_poll_table(html: str) -> Optional[dict[str, float]]:
    """
    Parse the most recent poll row from a Wikipedia polling table.
    Returns raw support percentages keyed by party/candidate name.
    """
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "lxml")

        # Find wikitables (polling tables)
        tables = soup.find_all("table", class_=lambda c: c and "wikitable" in c)
        if not tables:
            return None

        # Try each table looking for one with percentage data
        for table in tables:
            rows = table.find_all("tr")
            if len(rows) < 3:
                continue

            # Extract header row to map columns
            header_row = rows[0]
            headers = [th.get_text(strip=True).lower() for th in header_row.find_all(["th", "td"])]

            # Look for % or candidate columns
            has_pct_data = any(any(kw in h for kw in _PARTY_TO_SCENARIO) for h in headers)
            if not has_pct_data:
                continue

            # Find the most recent data row (usually last non-header row)
            for row in reversed(rows[1:]):
                cells = row.find_all(["td", "th"])
                if len(cells) < 3:
                    continue

                result = {}
                for i, header in enumerate(headers):
                    if i >= len(cells):
                        break
                    cell_text = cells[i].get_text(strip=True).replace("%", "").replace(",", ".").strip()
                    try:
                        pct = float(cell_text)
                        if 0 < pct <= 100:
                            result[header] = pct
                    except ValueError:
                        continue

                if len(result) >= 2:
                    return result

        return None

    except Exception as e:
        logger.warning(f"poll_fetcher parse error: {e}")
        return None


def _map_to_scenarios(raw: dict[str, float]) -> Optional[dict[str, float]]:
    """
    Aggregate raw party percentages into 4 scenario signals.
    Returns unnormalized signal dict (or None if too little data).
    """
    signals: dict[str, float] = {
        "centrist": 0.0,
        "national_rally": 0.0,
        "left_wing": 0.0,
        "hung_parliament": 0.0,
    }

    matched_total = 0.0
    for header, pct in raw.items():
        for keyword, scenario in _PARTY_TO_SCENARIO.items():
            if keyword in header.lower():
                signals[scenario] += pct
                matched_total += pct
                break

    if matched_total < 10:
        return None

    # Hung parliament signal: when no party has clear majority (>40%)
    top_signal = max(signals["centrist"], signals["national_rally"], signals["left_wing"])
    if top_signal < 40:
        # Fragmented — boost hung parliament
        fragmentation = max(0.0, (40 - top_signal) / 40)
        signals["hung_parliament"] = fragmentation * matched_total * 0.5

    return signals


def _fetch_page_sync(url: str) -> Optional[str]:
    """Synchronous HTTP fetch."""
    try:
        import urllib.request
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "FrancePoliticalIntelligenceMVP/0.1 (research; local)"},
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        logger.warning(f"poll_fetcher fetch failed for {url}: {e}")
        return None


async def fetch_wiki_poll_signal() -> dict[str, float]:
    """
    Fetch Wikipedia polling data and return scenario signals (0-100 scale, unnormalized).
    Returns {} on failure (graceful degradation).
    """
    loop = asyncio.get_event_loop()

    for url in _WIKI_PAGES:
        html = await loop.run_in_executor(None, _fetch_page_sync, url)
        if not html:
            continue

        raw = _parse_poll_table(html)
        if not raw:
            continue

        signals = _map_to_scenarios(raw)
        if signals and any(v > 0 for v in signals.values()):
            logger.info(f"poll_fetcher: got signals from {url}: {signals}")
            return signals

    logger.warning("poll_fetcher: no usable data from any Wikipedia page")
    return {}
