"""Optional AI layer: institutional-style bull/bear theses for the watchlist.

One Anthropic call per watchlist name (kept small on purpose -- running this
across 500 names daily would be costly). Output is attached to each stock as
record['ai'] and rendered in the detail drawer ONLY when present, so without an
API key / credits the UI simply omits the section (no placeholders).

Framed as impersonal, framework-based educational analysis -- never the views
of a real individual.
"""
import json
import os

import anthropic

SYSTEM = (
    "You are a financial-education tool producing concise, balanced, "
    "institutional-research-style analysis. Be concrete and even-handed: name "
    "real risks, not just upside. This is general educational commentary, not "
    "personalized advice, and not the view of any real person. "
    "Return ONLY valid JSON, no preamble or markdown."
)


def _one(client, model, r):
    prompt = (
        f"Stock: {r['symbol']} ({r.get('name')}). Sector: {r.get('sector')} / {r.get('industry')}. "
        f"Analyst consensus: {r.get('label')} (mean {r.get('consensus')}, {r.get('analysts')} analysts). "
        f"Implied upside to mean target: {r.get('upside')}%. "
        f"Fwd P/E {r.get('forward_pe')}, rev growth {r.get('revenue_growth')}%, "
        f"op margin {r.get('operating_margin')}%, ROE {r.get('roe')}%, RSI {r.get('rsi')}, trend {r.get('trend')}.\n\n"
        "Write a tight institutional view. Return JSON exactly as: "
        '{"bull":"2-3 sentence bull thesis","bear":"2-3 sentence bear thesis",'
        '"catalysts":"key near-term catalysts, one line","risks":"key risks, one line"}'
    )
    msg = client.messages.create(
        model=model, max_tokens=700, system=SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )
    text = "".join(b.text for b in msg.content if b.type == "text").strip()
    text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    return json.loads(text)


def attach(stocks, watchlist, model="claude-sonnet-4-6"):
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    by = {r["symbol"]: r for r in stocks}
    for sym in watchlist:
        r = by.get(sym.strip().upper())
        if not r:
            continue
        try:
            r["ai"] = _one(client, model, r)
        except Exception as e:
            print(f"     AI thesis failed for {sym}: {e}")
