"""Pick the universe to enrich: the top-N US common stocks by market cap.

Uses Yahoo's screener (via yfinance EquityQuery) rather than enriching all
~7,400 listed names -- ranking the full directory would require a market-cap
fetch per symbol, which the daily run cannot afford. The screener returns the
ranking directly, plus enough basic quote data (name, exchange, market cap) to
seed each record before the per-ticker enrichment pass.
"""
import time

import yfinance as yf
from yfinance import EquityQuery as EQ

# Yahoo caps a single screener page at 250 results.
_PAGE = 250


def top_us_by_marketcap(n: int = 500, min_cap: float = 1e9, sleep: float = 0.5):
    """Return up to `n` dicts: {symbol, name, exchange, market_cap}, biggest first.

    De-duplicates dual-class artifacts only by symbol (GOOG and GOOGL are both
    legitimately large and both kept). Foreign-listed lines are excluded by the
    region=us filter.
    """
    query = EQ("and", [EQ("eq", ["region", "us"]), EQ("gt", ["intradaymarketcap", min_cap])])
    out = []
    seen = set()
    offset = 0
    while len(out) < n:
        size = min(_PAGE, n - len(out))
        res = yf.screen(query, sortField="intradaymarketcap", sortAsc=False,
                        size=size, offset=offset)
        quotes = (res or {}).get("quotes", []) if isinstance(res, dict) else []
        if not quotes:
            break
        for q in quotes:
            sym = q.get("symbol")
            if not sym or sym in seen:
                continue
            seen.add(sym)
            out.append({
                "symbol": sym,
                "name": q.get("longName") or q.get("shortName") or q.get("displayName") or sym,
                "exchange": q.get("fullExchangeName") or q.get("exchange") or "",
                "market_cap": q.get("marketCap"),
            })
        offset += len(quotes)
        if len(quotes) < size:
            break
        time.sleep(sleep)
    return out[:n]


if __name__ == "__main__":
    rows = top_us_by_marketcap(10)
    for r in rows:
        print(f"{r['symbol']:8} {str(r['exchange']):14} {r['market_cap']:>18,} {r['name']}")
