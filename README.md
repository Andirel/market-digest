# The Consensus — daily NASDAQ/NYSE analyst-rating digest

A scheduled job that:

1. Pulls the full NASDAQ + NYSE common-stock universe from the official Nasdaq symbol directory.
2. Fetches analyst ratings per ticker and reduces them to a **1–5 consensus** (1 = Strong Buy … 5 = Strong Sell).
3. Optionally generates short- and long-term commentary on a small **watchlist** through five investing **frameworks** (Value, Macro, Quality, Growth, Contrarian), via the Anthropic API.
4. Renders a static HTML page and publishes it daily through GitHub Actions.

## Run it locally

```bash
pip install -r requirements.txt
UNIVERSE_LIMIT=25 python main.py        # cap while testing; drop it for the full run
open docs/index.html
```

To enable the watchlist commentary:

```bash
export ANTHROPIC_API_KEY=sk-ant-...
WATCHLIST="AAPL,MSFT,NVDA" python main.py
```

## Deploy (daily, automatic)

1. Push this repo to GitHub.
2. Repo → Settings → Secrets and variables → Actions → add `ANTHROPIC_API_KEY`.
3. Repo → Settings → Pages → set source to the **gh-pages** branch.
4. The workflow in `.github/workflows/daily.yml` runs every weekday at 09:30 UTC (and on demand from the Actions tab) and pushes the page to `gh-pages`.

---

## Three things to know before you scale or sell this

**Data source.** `yfinance` is an unofficial scraper of Yahoo. It's fine for prototyping and personal use, but it **will rate-limit** across thousands of tickers and is **not licensed for commercial redistribution**. Before charging anyone, move to a provider that grants redistribution rights — e.g. Financial Modeling Prep, Finnhub, Polygon, Tiingo, or Nasdaq Data Link. The only function you need to change is `fetch_one()` in `ratings.py`; keep its return shape and nothing else moves.

**The five "experts."** This generates analysis from named *frameworks*, not impersonations of real investors. Selling stock opinions attributed to specific living people (e.g. "AI Warren Buffett says buy NVDA") risks right-of-publicity and false-attribution claims and misleads buyers. The frameworks give you the same variety of viewpoints without that exposure. If you ever do reference real people, frame it explicitly as *influence/inspiration*, never as their actual opinion.

**Charging for access.** GitHub Pages is fully public — it **cannot** gate content. To monetize, pick one:
- Keep generating this static page but host it behind an auth layer: **Cloudflare Access**, **Netlify** + a members add-on, or a members CMS like **Ghost (members)**.
- Generate the page and deliver it to buyers via **Gumroad / Memberful / Substack / Stripe**.
- Free public teaser page (e.g. top 20 names) + paid full feed.

**Cost.** Ratings are free-ish (until you license a feed). LLM commentary is one API call per watchlist name per day — keep the watchlist small; don't run it over the whole universe.

**Legal.** Not legal or financial advice, and I'm not a lawyer. Publishing regular, *impersonal* commentary for a fee may fall under the U.S. investment-adviser "publisher's exemption," while *personalized* advice generally does not. The page carries a not-advice disclaimer. Talk to counsel before you charge.
