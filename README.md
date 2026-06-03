# The Consensus — institutional equity intelligence dashboard

A scheduled job that builds a fast, data-rich, fully client-side market terminal
and publishes it daily through GitHub Actions.

Each run:

1. **Selects the top 500 US stocks by market cap** via the Yahoo screener (`selection.py`).
2. **Enriches each name with real data** (`enrich.py`): market cap & tier, sector/industry,
   price, mean analyst target & implied upside, the full Strong-Buy→Strong-Sell rating
   distribution + 30-day consensus momentum, dividend yield, forward P/E, PEG, revenue/EPS
   growth, margins, ROE, and FCF yield.
3. **Computes technicals** from batched 1-year price history (`technicals.py` / `history.py`):
   1D/1W/1M/YTD/1Y returns, RSI(14), 50/200-DMA status, trend classification, and a sparkline.
4. **Tags themes** deterministically (`themes.py`) and **aggregates** sector rollups, peer/sector
   ranks, and dashboard headline metrics (`aggregate.py`).
5. *(Optional)* Generates **AI bull/bear theses** for a small watchlist (`insights.py`) when an
   Anthropic key + credits are present — rendered in the detail drawer only when available.
6. Writes a single **`docs/data.json`** and copies the static app from `web/` (`render.py`).

The dashboard (`web/index.html` + `app.js` + `styles.css`) is a zero-build static app loaded
from CDNs (**AG Grid Community** for the data grid, **ECharts** for the heatmap/charts). It
renders metric cards, a market heatmap, distribution/upside charts, and a spreadsheet-grade grid
with correct numeric/date/text sorting, multi-column sort (Ctrl/Shift-click), per-column number &
text filters, sector/theme/preset external filters, quick search (`/`), column show/hide + resize +
reorder + pin (persisted), compact & fullscreen modes, CSV export, and a row-click detail drawer.

**Everything shown is real data.** Fields a free source can't provide are omitted, not faked.
Empty cells mean the value was unavailable from the source on that run.

## Run it locally

```bash
pip install -r requirements.txt
TOP_N=40 python main.py          # small sample while testing; defaults to 500
cd docs && python -m http.server 8731   # then open http://localhost:8731
```

Optional AI theses for the watchlist (needs Anthropic credits):

```bash
export ANTHROPIC_API_KEY=sk-ant-...
WATCHLIST="AAPL,MSFT,NVDA" TOP_N=40 python main.py
```

Useful env knobs: `TOP_N`, `ENRICH_SLEEP`, `WATCHLIST`, `REUSE_CACHE=1` (reuse the local
`data/enrich_cache.json` to speed up repeated local runs).

## Deploy (daily, automatic)

1. Push to GitHub.
2. Settings → Pages → source = **gh-pages** branch.
3. *(Optional)* Settings → Secrets and variables → Actions → add `ANTHROPIC_API_KEY` for theses.
4. `.github/workflows/daily.yml` runs every weekday 09:30 UTC (and on demand) and publishes `docs/`.

---

## Things to know before you scale or sell this

**Data source.** `yfinance` is an unofficial scraper of Yahoo — fine for prototyping/personal use,
but it **rate-limits** and is **not licensed for commercial redistribution**. On hosted runners,
coverage on any given day can be sparser than a local run; that's throttling, not a bug. Before
charging anyone, move to a licensed feed (Financial Modeling Prep, Finnhub, Polygon, Tiingo, Nasdaq
Data Link). The seams to swap are `enrich.fetch_one`, `history.batch_technicals`, and
`selection.top_us_by_marketcap`.

**The AI theses** are impersonal, framework-style educational commentary — never attributed to real
individuals. One API call per watchlist name; keep the watchlist small.

**Charging for access.** GitHub Pages is fully public and can't gate content. To monetize, host the
generated page behind an auth layer (Cloudflare Access, Netlify members, Ghost members) or deliver
it via Gumroad/Memberful/Substack/Stripe; or free teaser + paid full feed.

**Legal.** Not legal or financial advice. The page carries a not-advice disclaimer. Publishing
regular *impersonal* commentary may fall under the U.S. investment-adviser "publisher's exemption";
*personalized* advice generally does not. Talk to counsel before you charge.
