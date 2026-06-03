"""Daily pipeline: select top-N US stocks by market cap -> enrich with real
fundamentals, analyst consensus, and technicals -> aggregate -> emit a single
docs/data.json that the static dashboard (web/) renders entirely client-side.

Env knobs:
  TOP_N            how many stocks to cover (default 500)
  ENRICH_SLEEP     per-ticker throttle in seconds (default 0.4)
  WATCHLIST        comma list given the optional AI lens treatment
  ANTHROPIC_API_KEY  if set, generate AI theses for the watchlist
"""
import json
import os
import time
from pathlib import Path

import selection
import enrich
import history
import aggregate
import render

OUT = Path("docs")
CACHE = Path("data/enrich_cache.json")

TOP_N = int(os.environ.get("TOP_N") or os.environ.get("UNIVERSE_LIMIT") or 500)
SLEEP = float(os.environ.get("ENRICH_SLEEP", "0.4"))
WATCHLIST = [s.strip().upper() for s in os.environ.get("WATCHLIST", "").split(",") if s.strip()]


def _load_cache():
    if CACHE.exists():
        try:
            return {r["symbol"]: r for r in json.loads(CACHE.read_text())}
        except Exception:
            return {}
    return {}


def main():
    OUT.mkdir(exist_ok=True)
    CACHE.parent.mkdir(parents=True, exist_ok=True)

    print(f"1/5 select top {TOP_N} by market cap")
    seeds = selection.top_us_by_marketcap(TOP_N)
    print(f"     {len(seeds)} symbols")

    print("2/5 enrich (fundamentals + consensus)")
    cache = _load_cache() if os.environ.get("REUSE_CACHE") else {}
    records = []
    for i, seed in enumerate(seeds, 1):
        if seed["symbol"] in cache:
            records.append(cache[seed["symbol"]])
            continue
        records.append(enrich.fetch_one(seed))
        if i % 50 == 0:
            print(f"     ...{i}/{len(seeds)}")
            CACHE.write_text(json.dumps(records))
            time.sleep(SLEEP)
        else:
            time.sleep(SLEEP)
    CACHE.write_text(json.dumps(records))

    print("3/5 technicals (batched price history)")
    tech = history.batch_technicals([r["symbol"] for r in records])
    history.merge(records, tech)

    print("4/5 aggregate")
    payload = aggregate.build(records)

    if WATCHLIST and os.environ.get("ANTHROPIC_API_KEY"):
        print(f"5/5 AI theses for {len(WATCHLIST)} watchlist names")
        try:
            import insights
            insights.attach(payload["stocks"], WATCHLIST)
        except Exception as e:
            print(f"     AI theses skipped: {e}")
    else:
        print("5/5 AI theses skipped (no watchlist or ANTHROPIC_API_KEY)")

    render.publish(OUT, payload)
    print("done")


if __name__ == "__main__":
    main()
