"""Batched price-history fetch. Downloading one symbol at a time would mean
~500 extra HTTP round-trips; yf.download pulls many at once, so technicals cost
a handful of chunked requests instead.

Returns {symbol: {price, changes, rsi, dma..., trend, sparkline}}.
"""
import time

import yfinance as yf

import technicals


def _chunks(seq, n):
    for i in range(0, len(seq), n):
        yield seq[i:i + n]


def _series_for(data, sym, multi):
    """Extract a clean (dates, closes) pair for one symbol from a yf.download frame."""
    try:
        df = data[sym] if multi else data
        closes = df["Close"].dropna()
    except Exception:
        return [], []
    return list(closes.index), [float(x) for x in closes.values]


def batch_technicals(symbols, chunk=50, sleep=1.0, period="1y"):
    out = {}
    syms = list(symbols)
    for group in _chunks(syms, chunk):
        try:
            data = yf.download(group, period=period, interval="1d",
                               group_by="ticker", auto_adjust=True,
                               threads=True, progress=False)
        except Exception:
            data = None
        multi = len(group) > 1
        for sym in group:
            dates, closes = ([], []) if data is None else _series_for(data, sym, multi)
            if not closes:
                out[sym] = {}
                continue
            ch = technicals.changes(closes)
            ch["YTD"] = technicals.ytd(closes, dates)
            ma = technicals.moving_averages(closes)
            out[sym] = {
                "price_hist": round(closes[-1], 2),
                "changes": ch,
                "rsi": technicals.rsi(closes),
                "sparkline": technicals.sparkline(closes),
                **ma,
            }
        time.sleep(sleep)
    return out


def merge(records, tech):
    """Fold technicals into records (in place) and return them.

    Falls back to the history close for price when .info had none.
    """
    for r in records:
        t = tech.get(r["symbol"], {})
        if not t:
            r.setdefault("changes", {})
            continue
        if not r.get("price"):
            r["price"] = t.get("price_hist")
            if r["price"] and r.get("price_target"):
                r["upside"] = round((r["price_target"] / r["price"] - 1.0) * 100.0, 2)
        r["changes"] = t.get("changes", {})
        r["rsi"] = t.get("rsi")
        r["dma50_status"] = t.get("dma50_status")
        r["dma200_status"] = t.get("dma200_status")
        r["trend"] = t.get("trend")
        r["sparkline"] = t.get("sparkline", [])
    return records
