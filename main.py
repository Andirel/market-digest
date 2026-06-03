"""Daily pipeline: universe -> ratings -> (optional) lens perspectives -> HTML."""
import os
from pathlib import Path

import tickers
import ratings as ratings_mod
import perspectives as persp_mod
import render

OUT = Path("docs")
OUT.mkdir(exist_ok=True)

# Featured names get the five-lens treatment (one API call each -- keep it small).
WATCHLIST = os.environ.get("WATCHLIST", "AAPL,MSFT,NVDA,AMZN,GOOGL").split(",")
# Cap the universe while testing so you don't wait on thousands of fetches.
_lim = os.environ.get("UNIVERSE_LIMIT")
UNIVERSE_LIMIT = int(_lim) if _lim else None


def main():
    print("1/4 universe")
    universe = tickers.get_universe()
    print(f"     {len(universe)} symbols")

    print("2/4 analyst ratings")
    rated = ratings_mod.build_ratings(universe, limit=UNIVERSE_LIMIT)

    print("3/4 lens perspectives")
    perspectives = {}
    if os.environ.get("ANTHROPIC_API_KEY"):
        perspectives = persp_mod.build(WATCHLIST, rated)
    else:
        print("     ANTHROPIC_API_KEY not set -- skipping perspectives")

    print("4/4 render")
    render.build_page(OUT / "index.html", rated, perspectives)
    print("done")


if __name__ == "__main__":
    main()
