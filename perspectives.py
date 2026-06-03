"""Generate short- and long-term commentary for a watchlist from five
named ANALYTICAL LENSES (schools of thought), via the Anthropic API.

Deliberately NOT impersonations of specific living investors. These are
generic investing frameworks, framed as educational analysis -- which keeps
you clear of right-of-publicity / false-attribution exposure and is a more
honest product than "AI Warren Buffett says buy."

Cost note: one API call per ticker. Running this across thousands of names
daily is expensive, so it defaults to a small watchlist. Generate lenses only
for the names you actually feature.
"""
import json
import os

import anthropic

LENSES = [
    ("Value / Margin-of-Safety",
     "intrinsic value vs price, durable competitive moats, balance-sheet strength, "
     "buying well below estimated worth, multi-year holding"),
    ("Global Macro / All-Weather",
     "how the name behaves across growth/inflation/rate regimes, diversification, "
     "sensitivity to the macro cycle and policy"),
    ("Quality Compounder",
     "return on invested capital, pricing power, reinvestment runway, management "
     "quality, consistency of compounding"),
    ("Growth / Innovation",
     "addressable-market expansion, revenue growth durability, disruption, optionality"),
    ("Contrarian / Special Situations",
     "sentiment extremes, mean reversion, catalysts, mispricing, what consensus may be missing"),
]

SYSTEM = (
    "You are a financial-education tool. For the given stock you produce brief, "
    "balanced analysis through several named investing FRAMEWORKS. These are "
    "schools of thought, not real individuals -- never attribute views to, name, "
    "or imitate specific people. Be concrete and even-handed: name real risks, not "
    "just upside. This is general educational commentary, not personalized advice. "
    "Return ONLY valid JSON, no preamble or markdown."
)


def build(watchlist, ratings_by_symbol, model="claude-sonnet-4-6"):
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    rmap = {r["symbol"]: r for r in ratings_by_symbol}
    out = {}
    lens_spec = "\n".join(f"- {name}: {focus}" for name, focus in LENSES)

    for sym in watchlist:
        sym = sym.strip().upper()
        ctx = rmap.get(sym, {})
        consensus = ctx.get("label", "unknown")
        prompt = (
            f"Stock: {sym} ({ctx.get('name', sym)}). "
            f"Current analyst consensus: {consensus} "
            f"(mean {ctx.get('mean')}, {ctx.get('analysts', 0)} analysts).\n\n"
            f"For EACH framework below, give a short_term view (next ~1-3 months) and a "
            f"long_term view (3+ years), 1-2 sentences each.\n{lens_spec}\n\n"
            'Return JSON shaped exactly as: '
            '{"lenses":[{"framework":"...","short_term":"...","long_term":"..."}]}'
        )
        try:
            msg = client.messages.create(
                model=model, max_tokens=1200,
                system=SYSTEM,
                messages=[{"role": "user", "content": prompt}],
            )
            text = "".join(b.text for b in msg.content if b.type == "text").strip()
            text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            out[sym] = json.loads(text)["lenses"]
        except Exception as e:
            print(f"  perspective failed for {sym}: {e}")
            out[sym] = []
    return out
