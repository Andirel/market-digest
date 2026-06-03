"""Post-enrichment aggregation: dashboard headline metrics, sector rollups for
the heatmap, per-stock sector ranks, and the default institutional ranking.

All derived from the real per-stock records -- no external calls.
"""


def _avg(vals):
    vals = [v for v in vals if v is not None]
    return round(sum(vals) / len(vals), 2) if vals else None


def default_rank_key(r):
    """Primary: lowest (most bullish) consensus. Secondary: most analysts.

    Uncovered names sink to the bottom; among covered names a 1-analyst microcap
    can't outrank a widely-covered Strong Buy because ties break on coverage.
    """
    has = r.get("consensus") is not None
    return (not has, r.get("consensus") if has else 9.0, -(r.get("analysts") or 0))


def sector_stats(records):
    """Rollup per sector for the heatmap/treemap and bull/bear superlatives."""
    by = {}
    for r in records:
        sec = r.get("sector") or "Unclassified"
        by.setdefault(sec, []).append(r)
    out = []
    for sec, rows in by.items():
        covered = [x for x in rows if x.get("consensus") is not None]
        out.append({
            "sector": sec,
            "count": len(rows),
            "market_cap": sum(x.get("market_cap") or 0 for x in rows),
            "avg_consensus": _avg([x.get("consensus") for x in covered]),
            "avg_upside": _avg([x.get("upside") for x in covered]),
            "avg_momentum": _avg([x.get("consensus_delta") for x in covered]),
        })
    out.sort(key=lambda s: s["market_cap"], reverse=True)
    return out


def assign_sector_ranks(records):
    """Rank each stock within its sector by consensus (then analyst count)."""
    by = {}
    for r in records:
        by.setdefault(r.get("sector") or "Unclassified", []).append(r)
    for rows in by.values():
        ranked = sorted(rows, key=default_rank_key)
        n = len(ranked)
        for i, r in enumerate(ranked, 1):
            r["sector_rank"] = i
            r["sector_size"] = n


def dashboard_stats(records, sectors):
    covered = [r for r in records if r.get("consensus") is not None]
    rated_sectors = [s for s in sectors if s["avg_consensus"] is not None]
    most_bull = min(rated_sectors, key=lambda s: s["avg_consensus"], default=None)
    most_bear = max(rated_sectors, key=lambda s: s["avg_consensus"], default=None)
    upgr_sectors = [s for s in sectors if s["avg_momentum"] is not None]
    # Most negative avg delta == sentiment improving most (lower score = bullish).
    most_upgr = min(upgr_sectors, key=lambda s: s["avg_momentum"], default=None)
    top_cov = max(records, key=lambda r: r.get("analysts") or 0, default=None)
    top_cap = max(records, key=lambda r: r.get("market_cap") or 0, default=None)
    return {
        "total": len(records),
        "covered": len(covered),
        "strong_buy": sum(1 for r in covered if r["consensus"] <= 1.5),
        "buy": sum(1 for r in covered if 1.5 < r["consensus"] <= 2.5),
        "sell": sum(1 for r in covered if r["consensus"] > 3.5),
        "avg_consensus": _avg([r["consensus"] for r in covered]),
        "avg_upside": _avg([r.get("upside") for r in covered]),
        "most_bullish_sector": most_bull["sector"] if most_bull else None,
        "most_bearish_sector": most_bear["sector"] if most_bear else None,
        "most_upgraded_sector": most_upgr["sector"] if most_upgr else None,
        "top_coverage": {"symbol": top_cov["symbol"], "analysts": top_cov.get("analysts")} if top_cov else None,
        "largest": {"symbol": top_cap["symbol"], "market_cap": top_cap.get("market_cap")} if top_cap else None,
    }


def build(records):
    """Annotate records in place and return the full dashboard payload."""
    sectors = sector_stats(records)
    assign_sector_ranks(records)
    records.sort(key=default_rank_key)
    return {
        "stats": dashboard_stats(records, sectors),
        "sectors": sectors,
        "stocks": records,
    }
