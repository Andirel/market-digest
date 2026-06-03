"""Pull analyst recommendation data per ticker and reduce it to a single
1-5 consensus score (1 = Strong Buy ... 5 = Strong Sell), matching the
scale Yahoo/most terminals use.

Uses yfinance, which is an UNOFFICIAL scraper of Yahoo. Fine for prototyping
and personal use; NOT licensed for commercial redistribution and WILL get
rate-limited across thousands of symbols. The `fetch_one` function is the
single seam to swap in a licensed provider (FMP/Finnhub/Polygon/Tiingo) later
-- keep its return shape and the rest of the pipeline is unchanged.
"""
import json
import time
from pathlib import Path

import yfinance as yf

SCALE = {"strongBuy": 1, "buy": 2, "hold": 3, "sell": 4, "strongSell": 5}
LABELS = {1: "Strong Buy", 2: "Buy", 3: "Hold", 4: "Sell", 5: "Strong Sell"}


def _mean_from_counts(row: dict):
    total = sum(int(row.get(k, 0) or 0) for k in SCALE)
    if not total:
        return None, 0
    score = sum(SCALE[k] * int(row.get(k, 0) or 0) for k in SCALE) / total
    return round(score, 2), total


def _label(score):
    if score is None:
        return "No coverage"
    return LABELS[min(5, max(1, round(score)))]


def consensus_from_recommendations(rec):
    """Reduce a yfinance recommendations DataFrame to a rich consensus dict.

    Returns the full 1-5 distribution, the weighted mean + label + analyst
    count for the current month, and momentum vs. the oldest available month
    (3 months back) so the UI can show direction, not just a static score.
    Returns None when there is no coverage at all.
    """
    if rec is None or len(rec) == 0:
        return None
    rows = rec.to_dict("records") if hasattr(rec, "to_dict") else list(rec)
    if "period" in (rec.columns if hasattr(rec, "columns") else []):
        cur = next((r for r in rows if r.get("period") == "0m"), rows[0])
        prev = next((r for r in reversed(rows) if r.get("period") != "0m"), None)
    else:
        cur, prev = rows[0], (rows[-1] if len(rows) > 1 else None)

    mean, n = _mean_from_counts(cur)
    if mean is None:
        return None
    dist = {k: int(cur.get(k, 0) or 0) for k in SCALE}
    prev_mean = _mean_from_counts(prev)[0] if prev else None
    delta = round(mean - prev_mean, 2) if prev_mean is not None else None
    # Lower score = more bullish, so a negative delta is an upgrade in sentiment.
    if delta is None or abs(delta) < 0.02:
        direction = "flat"
    else:
        direction = "up" if delta < 0 else "down"
    return {
        "mean": mean,
        "label": _label(mean),
        "analysts": n,
        "distribution": dist,
        "prev_mean": prev_mean,
        "delta": delta,
        "direction": direction,
    }


def fetch_one(yahoo_symbol: str):
    """Return {'mean': float, 'label': str, 'analysts': int} or None.

    SWAP POINT: replace this body with a call to your licensed data API.
    """
    try:
        rec = yf.Ticker(yahoo_symbol).get_recommendations()
    except Exception:
        return None
    if rec is None or len(rec) == 0:
        return None
    if "period" in rec.columns:
        cur = rec[rec["period"] == "0m"]
        row = (cur.iloc[0] if len(cur) else rec.iloc[0]).to_dict()
    else:
        row = rec.iloc[-1].to_dict()
    score, n = _mean_from_counts(row)
    if score is None:
        return None
    return {"mean": score, "label": _label(score), "analysts": n}


def build_ratings(universe, limit=None, sleep=0.4, cache=Path("data/ratings.json")):
    """Iterate the universe, fetch each rating, write a checkpointed JSON cache.

    Throttled and restart-safe: re-running skips symbols already in the cache,
    so a long run that dies partway can resume.
    """
    cache.parent.mkdir(parents=True, exist_ok=True)
    done = {}
    if cache.exists():
        done = {r["symbol"]: r for r in json.loads(cache.read_text())}

    rows = universe.itertuples(index=False)
    results = list(done.values())
    seen = set(done)
    processed = 0
    for r in rows:
        if limit and processed >= limit:
            break
        if r.symbol in seen:
            continue
        processed += 1
        data = fetch_one(r.yahoo_symbol)
        rec = {
            "symbol": r.symbol,
            "name": r.name,
            "exchange": r.exchange,
            "mean": data["mean"] if data else None,
            "label": data["label"] if data else "No coverage",
            "analysts": data["analysts"] if data else 0,
        }
        results.append(rec)
        seen.add(r.symbol)
        if processed % 50 == 0:
            cache.write_text(json.dumps(results))
            print(f"  ...{processed} fetched")
        time.sleep(sleep)

    cache.write_text(json.dumps(results))
    # Sort: covered names first, strongest buys at top.
    results.sort(key=lambda x: (x["mean"] is None, x["mean"] if x["mean"] else 9))
    return results
