"""Technical indicators computed from real daily-close history.

All inputs are a pandas Series of closes (oldest -> newest). Every function
guards against short series and returns None when it can't be computed, so the
UI shows a blank cell rather than a fabricated value.
"""
import math


def _pct(a, b):
    if a is None or b is None or b == 0:
        return None
    return round((a / b - 1.0) * 100.0, 2)


def changes(closes):
    """Return {'1D','1W','1M','YTD','1Y'} percent changes (or None each)."""
    s = [float(x) for x in closes if x is not None and not (isinstance(x, float) and math.isnan(x))]
    if len(s) < 2:
        return {k: None for k in ("1D", "1W", "1M", "YTD", "1Y")}
    last = s[-1]
    def back(n):
        return s[-(n + 1)] if len(s) > n else s[0]
    return {
        "1D": _pct(last, back(1)),
        "1W": _pct(last, back(5)),
        "1M": _pct(last, back(21)),
        "1Y": _pct(last, s[0]),
        # YTD is filled by changes_with_dates() when a date index is available.
        "YTD": None,
    }


def ytd(closes, dates):
    """YTD % using the last close of the prior year as the base."""
    pairs = [(d, float(c)) for d, c in zip(dates, closes)
             if c is not None and not (isinstance(c, float) and math.isnan(c))]
    if len(pairs) < 2:
        return None
    cur_year = pairs[-1][0].year
    base = None
    for d, c in pairs:
        if d.year < cur_year:
            base = c          # keep last close from a prior year
        else:
            break
    if base is None:
        base = pairs[0][1]    # history doesn't reach last year; use earliest
    return _pct(pairs[-1][1], base)


def rsi(closes, period: int = 14):
    s = [float(x) for x in closes if x is not None and not (isinstance(x, float) and math.isnan(x))]
    if len(s) <= period:
        return None
    gains, losses = [], []
    for i in range(1, len(s)):
        d = s[i] - s[i - 1]
        gains.append(max(d, 0.0))
        losses.append(max(-d, 0.0))
    # Wilder's smoothing.
    avg_g = sum(gains[:period]) / period
    avg_l = sum(losses[:period]) / period
    for i in range(period, len(gains)):
        avg_g = (avg_g * (period - 1) + gains[i]) / period
        avg_l = (avg_l * (period - 1) + losses[i]) / period
    if avg_l == 0:
        return 100.0
    rs = avg_g / avg_l
    return round(100.0 - 100.0 / (1.0 + rs), 1)


def _sma(s, n):
    return sum(s[-n:]) / n if len(s) >= n else None


def moving_averages(closes):
    """Return DMA values, above/below status, and a trend classification."""
    s = [float(x) for x in closes if x is not None and not (isinstance(x, float) and math.isnan(x))]
    if not s:
        return {"dma50": None, "dma200": None, "dma50_status": None,
                "dma200_status": None, "trend": None}
    price = s[-1]
    d50, d200 = _sma(s, 50), _sma(s, 200)
    def status(ma):
        if ma is None:
            return None
        return "Above" if price >= ma else "Below"
    trend = None
    if d50 and d200:
        if price > d50 > d200:
            trend = "Strong Uptrend"
        elif price > d200:
            trend = "Uptrend"
        elif price < d50 < d200:
            trend = "Strong Downtrend"
        else:
            trend = "Downtrend"
    elif d200:
        trend = "Uptrend" if price > d200 else "Downtrend"
    return {
        "dma50": round(d50, 2) if d50 else None,
        "dma200": round(d200, 2) if d200 else None,
        "dma50_status": status(d50),
        "dma200_status": status(d200),
        "trend": trend,
    }


def sparkline(closes, points: int = 40):
    """Downsample the close series to ~`points` floats for an inline chart."""
    s = [round(float(x), 2) for x in closes
         if x is not None and not (isinstance(x, float) and math.isnan(x))]
    if len(s) <= points:
        return s
    step = len(s) / points
    return [s[min(len(s) - 1, int(i * step))] for i in range(points)]
