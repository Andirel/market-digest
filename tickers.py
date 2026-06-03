"""Build the NASDAQ + NYSE common-stock universe from the official
Nasdaq Trader symbol directory (free, authoritative, no scraping).

nasdaqlisted.txt -> NASDAQ
otherlisted.txt  -> NYSE (N), NYSE American (A), Arca (P), Cboe (Z), IEX (V)
"""
import io
import pandas as pd
import requests

NASDAQ_URL = "https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"
OTHER_URL = "https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"

EXCHANGE_NAMES = {
    "N": "NYSE", "A": "NYSE American", "P": "NYSE Arca",
    "Z": "Cboe BZX", "V": "IEX",
}


def _download(url: str) -> str:
    r = requests.get(url, timeout=30, headers={"User-Agent": "market-digest/1.0"})
    r.raise_for_status()
    return r.text


def get_universe(include_etfs: bool = False, exchanges=("N", "A")) -> pd.DataFrame:
    """Return a DataFrame: symbol, name, exchange, yahoo_symbol.

    `exchanges` filters the 'otherlisted' file. Default keeps NYSE + NYSE
    American only; add "P"/"Z"/"V" if you want Arca/Cboe/IEX too.
    """
    # --- NASDAQ ---
    nd = pd.read_csv(io.StringIO(_download(NASDAQ_URL)), sep="|")
    nd = nd[nd["Symbol"].notna() & (nd["Test Issue"] == "N")]
    if not include_etfs:
        nd = nd[nd["ETF"] != "Y"]
    nasdaq = pd.DataFrame({
        "symbol": nd["Symbol"],
        "name": nd["Security Name"],
        "exchange": "NASDAQ",
    })

    # --- NYSE / others ---
    ot = pd.read_csv(io.StringIO(_download(OTHER_URL)), sep="|")
    ot = ot[ot["ACT Symbol"].notna() & (ot["Test Issue"] == "N")]
    if not include_etfs:
        ot = ot[ot["ETF"] != "Y"]
    ot = ot[ot["Exchange"].isin(exchanges)]
    other = pd.DataFrame({
        "symbol": ot["ACT Symbol"],
        "name": ot["Security Name"],
        "exchange": ot["Exchange"].map(EXCHANGE_NAMES).fillna(ot["Exchange"]),
    })

    df = pd.concat([nasdaq, other], ignore_index=True)
    df = df.dropna(subset=["symbol"])
    # Drop the trailing "File Creation Time" footer row if it slipped through.
    df = df[~df["symbol"].str.contains("File Creation Time", na=False)]
    df = df.drop_duplicates(subset=["symbol"]).sort_values("symbol").reset_index(drop=True)
    # Class shares: Nasdaq uses BRK.B / BF.B; Yahoo expects BRK-B / BF-B.
    df["yahoo_symbol"] = df["symbol"].str.replace(".", "-", regex=False)
    return df


if __name__ == "__main__":
    u = get_universe()
    print(f"{len(u)} symbols")
    print(u.head(10).to_string(index=False))
