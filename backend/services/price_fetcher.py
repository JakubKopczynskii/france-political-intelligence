"""
Fetches closing prices for CAC40 companies via yfinance (Yahoo Finance).
No API key required. Data is publicly available.

What data leaves the machine: ticker symbols are sent to Yahoo Finance servers.
No portfolio holdings, positions, or personal data are sent.
"""
import asyncio
from datetime import date
from typing import Optional
from sqlalchemy.orm import Session

try:
    import yfinance as yf
    _YFINANCE_AVAILABLE = True
except ImportError:
    _YFINANCE_AVAILABLE = False

from models import PriceCache

CAC40_TICKERS = [
    "AI.PA", "AIR.PA", "CS.PA", "BNP.PA", "EN.PA", "CAP.PA", "CA.PA",
    "SGO.PA", "ACA.PA", "DSY.PA", "EL.PA", "EUFI.PA", "RMS.PA", "KER.PA",
    "OR.PA", "LR.PA", "MC.PA", "ML.PA", "ORA.PA", "RI.PA", "PUB.PA",
    "RNO.PA", "SAN.PA", "SAF.PA", "STM.PA", "GLE.PA", "STLAP.PA",
    "TTE.PA", "URW.PA", "VIE.PA", "DG.PA", "WLN.PA", "SU.PA",
    "SW.PA", "ENGI.PA", "VIV.PA", "FP.PA", "HO.PA", "BN.PA", "EURAZ.PA",
]


def fetch_prices_sync(tickers: list) -> dict:
    """Fetch latest closing prices synchronously. Returns {ticker: price_or_None}."""
    if not _YFINANCE_AVAILABLE:
        return {t: None for t in tickers}

    prices = {}
    try:
        data = yf.download(tickers, period="5d", auto_adjust=True, progress=False)
        # yfinance returns MultiIndex columns when multiple tickers
        try:
            close = data["Close"]
        except (KeyError, TypeError):
            return {t: None for t in tickers}

        for ticker in tickers:
            try:
                if hasattr(close, "columns") and ticker in close.columns:
                    col = close[ticker].dropna()
                    prices[ticker] = float(col.iloc[-1]) if len(col) > 0 else None
                elif hasattr(close, "iloc"):
                    # Single ticker — close is a Series
                    col = close.dropna()
                    prices[ticker] = float(col.iloc[-1]) if len(col) > 0 else None
                else:
                    prices[ticker] = None
            except Exception:
                prices[ticker] = None
    except Exception:
        return {t: None for t in tickers}
    return prices


async def refresh_prices(db: Session) -> int:
    """
    Fetch prices for all CAC40 tickers and upsert into PriceCache.
    Returns count of tickers successfully updated.
    Runs the synchronous yfinance call in a thread executor to avoid blocking.
    """
    if not _YFINANCE_AVAILABLE:
        return 0

    today = date.today().isoformat()
    loop = asyncio.get_event_loop()
    prices = await loop.run_in_executor(None, fetch_prices_sync, CAC40_TICKERS)

    count = 0
    for ticker, price in prices.items():
        if price is None:
            continue
        # Delete any existing entry for today before inserting
        db.query(PriceCache).filter(
            PriceCache.ticker == ticker,
            PriceCache.price_date == today,
        ).delete()
        db.add(PriceCache(ticker=ticker, price=price, currency="EUR", price_date=today))
        count += 1

    db.commit()
    return count


def get_cached_price(db: Session, ticker: str) -> Optional[float]:
    """Return today's cached price for a ticker, or None if not cached."""
    today = date.today().isoformat()
    entry = (
        db.query(PriceCache)
        .filter(PriceCache.ticker == ticker, PriceCache.price_date == today)
        .order_by(PriceCache.fetched_at.desc())
        .first()
    )
    return entry.price if entry else None


def yfinance_available() -> bool:
    return _YFINANCE_AVAILABLE
