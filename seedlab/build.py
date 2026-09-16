"""Provider symbol resolution and build integrity checks."""
import json
from pathlib import Path
import refresh

# Yahoo distinguishes Hyperliquid from unrelated assets sharing HYPE.
# Source: https://finance.yahoo.com/quote/HYPE32196-USD/
PROVIDER_SYMBOLS = {'HYPE': 'HYPE32196-USD'}
base_universe = refresh.universe

def resolved_universe():
    rows = base_universe()
    for row in rows:
        row['symbol'] = PROVIDER_SYMBOLS.get(row['ticker'], row['symbol'])
    return rows

refresh.universe = resolved_universe

if __name__ == '__main__':
    assert len(resolved_universe()) == 30
    assert len({r['ticker'] for r in resolved_universe()}) == 30
    assert refresh.rsi(range(40)) == 100
    assert refresh.rsi(range(40, 0, -1)) == 0
    assert refresh.rsi([10] * 40) == 50
    refresh.main()
    data = json.loads((Path(__file__).parent / 'data.json').read_text())
    for row in data['assets'] + data['core']:
        if row.get('status') == 'fresh':
            assert row['price'] > 0
            assert 0 <= row['rsi'] <= 100
            assert row['low52'] <= row['price'] <= row['high52']
            assert abs(row['histogram'] - (row['macd'] - row['signal'])) < 0.000003
        if row['kind'] != 'equity':
            assert row.get('ratings') is None
    print('Validated: 30 unique research assets, 2 anchors, valid RSI/MACD/ranges, no synthetic crypto consensus.')
