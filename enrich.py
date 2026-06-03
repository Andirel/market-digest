"""Per-ticker enrichment: turn a seed {symbol,name,exchange,market_cap} into a
full record by pulling real fundamentals (.info) + analyst recommendations, and
merging in technicals computed from batched price history (see history.py).

Every field is real or None. Nothing is interpolated or invented.
"""
import math

import yfinance as yf

import ratings
import themes

_CAP_TIERS = [
    (200e9, "Mega"), (10e9, "Large"), (2e9, "Mid"),
    (300e6, "Small"), (0, "Micro"),
]


def _num(x):
    """Coerce to float, mapping NaN/inf/missing to None."""
    if x is None:
        return None
    try:
        f = float(x)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(f) or math.isinf(f) else f


def _pct(x):
    """yfinance ratios are fractions (0.166); present as percent (16.6)."""
    f = _num(x)
    return round(f * 100.0, 2) if f is not None else None


def cap_category(mc):
    if mc is None:
        return None
    for floor, name in _CAP_TIERS:
        if mc >= floor:
            return name
    return "Micro"


def fetch_one(seed: dict) -> dict:
    """Build a record for one symbol. `seed` comes from selection.top_us_by_marketcap."""
    sym = seed["symbol"]
    rec = {
        "symbol": sym,
        "name": seed.get("name") or sym,
        "exchange": seed.get("exchange") or "",
        "market_cap": _num(seed.get("market_cap")),
        "sector": None, "industry": None, "price": None, "price_target": None,
        "upside": None, "analysts": 0, "dividend_yield": None, "forward_pe": None,
        "peg": None, "revenue_growth": None, "eps_growth": None, "gross_margin": None,
        "operating_margin": None, "roe": None, "fcf_yield": None,
        "consensus": None, "label": "No coverage", "distribution": None,
        "consensus_prev": None, "consensus_delta": None, "consensus_dir": "flat",
        "themes": [],
    }

    tk = yf.Ticker(sym)
    try:
        info = tk.info or {}
    except Exception:
        info = {}

    if info:
        rec["sector"] = info.get("sector")
        rec["industry"] = info.get("industry")
        rec["name"] = info.get("longName") or info.get("shortName") or rec["name"]
        rec["market_cap"] = _num(info.get("marketCap")) or rec["market_cap"]
        rec["price"] = _num(info.get("currentPrice")) or _num(info.get("regularMarketPrice"))
        rec["price_target"] = _num(info.get("targetMeanPrice"))
        rec["analysts"] = int(info.get("numberOfAnalystOpinions") or 0)
        rec["dividend_yield"] = _num(info.get("dividendYield"))  # already a percent in v1.x
        rec["forward_pe"] = _num(info.get("forwardPE"))
        rec["peg"] = _num(info.get("trailingPegRatio"))
        rec["revenue_growth"] = _pct(info.get("revenueGrowth"))
        rec["eps_growth"] = _pct(info.get("earningsGrowth"))
        rec["gross_margin"] = _pct(info.get("grossMargins"))
        rec["operating_margin"] = _pct(info.get("operatingMargins"))
        rec["roe"] = _pct(info.get("returnOnEquity"))
        fcf, mc = _num(info.get("freeCashflow")), rec["market_cap"]
        if fcf is not None and mc:
            rec["fcf_yield"] = round(fcf / mc * 100.0, 2)

    if rec["price"] and rec["price_target"]:
        rec["upside"] = round((rec["price_target"] / rec["price"] - 1.0) * 100.0, 2)

    rec["market_cap_category"] = cap_category(rec["market_cap"])
    rec["themes"] = themes.tag(rec["name"], rec.get("sector") or "", rec.get("industry") or "")

    try:
        cons = ratings.consensus_from_recommendations(tk.get_recommendations())
    except Exception:
        cons = None
    if cons:
        rec["consensus"] = cons["mean"]
        rec["label"] = cons["label"]
        rec["analysts"] = cons["analysts"] or rec["analysts"]
        rec["distribution"] = cons["distribution"]
        rec["consensus_prev"] = cons["prev_mean"]
        rec["consensus_delta"] = cons["delta"]
        rec["consensus_dir"] = cons["direction"]

    return rec
