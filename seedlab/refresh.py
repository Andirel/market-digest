"""Public-market research only. No brokerage credentials, holdings or trading.
Run with Python 3.12: pip install yfinance pandas numpy; python seedlab/refresh.py
All signals use completed daily bars. Missing data is never fabricated.
"""
from __future__ import annotations
import datetime as dt
import json, math, os, time, urllib.request
from pathlib import Path
from zoneinfo import ZoneInfo
ROOT=Path(__file__).resolve().parent
# Editorial research judgments, not sell-side ratings or forecasts.
# ticker|name|theme|risk 1-5|stage|minimum horizon|thesis|monitor|risk|official website
RAW='''TSM|Taiwan Semiconductor|ai|3|Established|5|Advanced-chip manufacturing infrastructure.|Advanced-node utilization, margins and customer demand.|Taiwan concentration, capital intensity and chip cyclicality.|https://investor.tsmc.com/
VRT|Vertiv|ai|3|Established|5|Power and cooling for increasingly dense data centers.|Organic orders, cash conversion and backlog quality.|AI spending slowdown, competition and expensive valuation.|https://investors.vertiv.com/
CRDO|Credo Technology|ai|4|Scaling|7|High-speed connectivity inside AI and cloud networks.|Customer diversification and production design wins.|Customer concentration and competing interconnect technologies.|https://investors.credosemi.com/
ALAB|Astera Labs|ai|4|Scaling|7|Connectivity silicon for complex AI systems.|Product ramps, customer mix and gross margins.|Hyperscaler concentration, competition and valuation.|https://ir.asteralabs.com/
NBIS|Nebius|ai|5|Scaling|10|Independent cloud infrastructure for AI computing.|Utilization, contracted unit economics and financing.|Capital intensity, dilution and idle computing capacity.|https://nebius.com/investor-hub
NET|Cloudflare|ai|4|Scaling|7|Security, edge networking and developer infrastructure.|Large-customer expansion and free cash flow per share.|Premium valuation, competition and stock compensation.|https://cloudflare.net/
PLTR|Palantir|ai|4|Established|7|Enterprise and government software for operational AI.|Commercial adoption, retention and per-share earnings.|Expectations and valuation can outrun business progress.|https://investors.palantir.com/
SYM|Symbotic|ai|4|Scaling|7|Warehouse robotics and large-scale automation.|Installations, project profitability and customer mix.|Customer concentration and difficult deployments.|https://ir.symbotic.com/
GEV|GE Vernova|power|3|Established|5|Generation and grid equipment for electricity investment.|Backlog conversion, service revenues and cash flow.|Order execution, cancellations and valuation.|https://www.gevernova.com/investors
CCJ|Cameco|power|3|Established|5|Uranium supply and nuclear-services exposure.|Contract prices, mine output and Westinghouse performance.|Uranium cyclicality, operational disruption and policy.|https://www.cameco.com/invest
LEU|Centrus Energy|power|4|Scaling|7|Nuclear enrichment and advanced-fuel capability.|Funded contracts, commercial capacity and capital needs.|Policy dependence, supply restrictions and scaling risk.|https://investors.centrusenergy.com/
OKLO|Oklo|power|5|Binary|10|Long-duration option on commercial advanced nuclear power.|Licensing, funded construction and delivered electricity.|First-of-kind economics, delays and dilution.|https://oklo.com/investors/
CEG|Constellation Energy|power|3|Established|5|Existing generation capacity and contracted electricity demand.|Power contracts, plant performance and capital allocation.|Power prices, plant outages and regulation.|https://investors.constellationenergy.com/
RKLB|Rocket Lab|space|4|Scaling|7|Launch, spacecraft and components for the space economy.|Launch economics, Neutron milestones and cash runway.|Launch failure, schedule delays and capital needs.|https://investors.rocketlabcorp.com/
ASTS|AST SpaceMobile|space|5|Binary|10|Satellite connectivity directly to everyday phones.|Deployment, coverage and monetized subscribers.|Constellation funding, execution and competition.|https://investors.ast-science.com/
AVAV|AeroVironment|space|4|Established|5|Autonomous defense, drones and counter-drone systems.|Funded orders, integration and cash conversion.|Procurement timing, integration and program concentration.|https://investor.avinc.com/
KTOS|Kratos Defense|space|4|Scaling|7|Lower-cost autonomous aircraft and defense systems.|Programs moving from development to production.|Budget delays, program failures and production execution.|https://ir.kratosdefense.com/
HOOD|Robinhood|finance|4|Established|5|A broader consumer platform for investing and finance.|Net deposits, funded accounts and recurring revenue.|Trading cyclicality, regulation and competition.|https://investors.robinhood.com/
MELI|MercadoLibre|finance|3|Established|5|Integrated Latin American commerce and payments.|Commerce growth, credit losses and unit economics.|Currency, competition, credit and reinvestment pressure.|https://investor.mercadolibre.com/
NU|Nu Holdings|finance|3|Established|5|Digital financial services with emerging-market scale.|Active customers, revenue per customer and credit quality.|Consumer credit losses, currency and expansion costs.|https://www.investidores.nu/en/
SOFI|SoFi|finance|4|Established|5|Digital banking, lending and financial-service cross-selling.|Deposits, fee revenue and loan performance.|Credit cycles, funding costs and dilution.|https://investors.sofi.com/
COIN|Coinbase|finance|4|Established|7|Exchange, custody and infrastructure for crypto markets.|Trading economics and recurring platform revenue.|Crypto-market dependence, regulation and competition.|https://investor.coinbase.com/
CRSP|CRISPR Therapeutics|health|5|Binary|10|Gene-editing therapies with multiple clinical opportunities.|Treatment uptake, clinical data and cash runway.|Trial failure, reimbursement and commercialization.|https://ir.crisprtx.com/
TMDX|TransMedics|health|4|Scaling|7|Organ-transplant technology with an integrated service model.|Clinical adoption, utilization and operating margins.|Reimbursement, clinical execution and logistics costs.|https://investors.transmedics.com/
LINK|Chainlink|crypto|4|Token|7|Oracle and interoperability infrastructure for blockchains.|Service fees translating into durable LINK demand.|Network adoption may not create proportional token value.|https://chain.link/economics
ETH|Ethereum|crypto|4|Token|7|Settlement and application infrastructure for tokenized finance.|Fee economics, usage, staking and scaling tradeoffs.|Competition, technical risk and weak token value capture.|https://ethereum.org/
SOL|Solana|crypto|5|Token|7|High-throughput infrastructure for applications and payments.|Durable users, fees and network reliability.|Speculative usage, competition and supply growth.|https://solana.com/
HYPE|Hyperliquid|crypto|5|Token|10|Onchain trading and exchange infrastructure.|Organic volume, fee capture and token releases.|Regulation, smart-contract risk and concentration.|https://hyperliquid.gitbook.io/hyperliquid-docs
AAVE|Aave|crypto|5|Token|7|Decentralized borrowing and lending infrastructure.|Bad debt, fee economics and governance decisions.|Contract exploits, collateral shocks and value capture.|https://aave.com/
ONDO|Ondo|crypto|5|Token|10|An option on growth in a tokenized-finance ecosystem.|Token-holder rights, unlocks and actual economic capture.|ONDO is not equity or a claim on tokenized-asset yields.|https://docs.ondo.foundation/'''
def universe():
    out=[]
    for line in RAW.splitlines():
        s,n,t,r,m,h,th,mo,br,url=line.split('|')
        out.append(dict(ticker=s,symbol=s+'-USD' if t=='crypto' else s,name=n,theme=t,risk=int(r),stage=m,minHorizon=int(h),thesis=th,monitor=mo,breakRisk=br,officialUrl=url,kind='crypto' if t=='crypto' else 'equity',researchAsOf='2026-09-16'))
    return out
CORE=[dict(ticker='VTI',symbol='VTI',name='Total US Stock Market ETF',theme='core',risk=2,kind='fund',thesis='Broad equity diversification; still subject to stock-market losses.',officialUrl='https://investor.vanguard.com/investment-products/etfs/profile/vti'),dict(ticker='SGOV',symbol='SGOV',name='0-3 Month Treasury Bond ETF',theme='reserve',risk=1,kind='fund',thesis='Short Treasury exposure; an ETF, not an FDIC-insured deposit.',officialUrl='https://www.ishares.com/us/products/314116/ishares-0-3-month-treasury-bond-etf')]
def num(x):
    try:
        x=float(x)
        return round(x,6) if math.isfinite(x) else None
    except (TypeError,ValueError): return None

def rsi(values,n=14):
    a=[float(x) for x in values]
    if len(a)<n+1:return None
    d=[a[i]-a[i-1] for i in range(1,len(a))]
    gains=[max(x,0) for x in d];losses=[max(-x,0) for x in d]
    g=sum(gains[:n])/n;l=sum(losses[:n])/n
    for i in range(n,len(d)):g=(g*(n-1)+gains[i])/n;l=(l*(n-1)+losses[i])/n
    return 50.0 if g==0 and l==0 else (100.0 if l==0 else 100-100/(1+g/l))

def calculate(asset,old,now):
    import yfinance as yf
    import numpy as np
    row=dict(asset);s=asset['symbol']
    row.update(attemptedAt=now.isoformat(),source='Yahoo Finance via yfinance',sourceUrl=f'https://finance.yahoo.com/quote/{s}/')
    try:
        obj=yf.Ticker(s);hist=obj.history(period='2y',interval='1d',auto_adjust=False,actions=False,raise_errors=True)
        if hist is None or hist.empty:raise ValueError('Empty history')
        if asset['kind']=='crypto':cutoff=now.date()
        else:
            local=now.astimezone(ZoneInfo('America/New_York'))
            cutoff=local.date()+dt.timedelta(days=1 if local.hour>=17 else 0)
        hist=hist[[x.date()<cutoff for x in hist.index]].dropna(subset=['Close'])
        if len(hist)<60:raise ValueError('Insufficient complete daily bars')
        c=hist['Close'].astype(float);p=float(c.iloc[-1]);end=hist.index[-1].date()
        one=hist[[x.date()>end-dt.timedelta(days=365) for x in hist.index]]
        lo=float(one['Low'].min());hi=float(one['High'].max())
        macd=c.ewm(span=12,adjust=False).mean()-c.ewm(span=26,adjust=False).mean()
        signal=macd.ewm(span=9,adjust=False).mean();delta=macd-signal
        d=float(delta.iloc[-1]);prev=float(delta.iloc[-2]);cross='Bullish crossover' if d>0>=prev else ('Bearish crossover' if d<0<=prev else None)
        def change(days):
            prevc=c[[x.date()<=end-dt.timedelta(days=days) for x in c.index]]
            return num((p/float(prevc.iloc[-1])-1)*100) if len(prevc) else None
        info={}
        try:info=obj.get_info() or {}
        except Exception:pass
        ratings=None
        if asset['kind']=='equity':
            try:
                rec=obj.get_recommendations()
                if rec is not None and not rec.empty:
                    active=rec[rec['period']=='0m'] if 'period' in rec else rec
                    rr=(active if not active.empty else rec).iloc[0]
                    counts=[int(rr.get(k,0) or 0) for k in ['strongBuy','buy','hold','sell','strongSell']];count=sum(counts)
                    if count:ratings=dict(counts=counts,count=count,score=num(sum((i+1)*x for i,x in enumerate(counts))/count),period=str(rr.get('period','latest')),retrievedAt=now.isoformat())
            except Exception:pass
        year=365 if asset['kind']=='crypto' else 252
        vol=np.log(c/c.shift(1)).dropna().tail(year).std()*np.sqrt(year)*100
        row.update(price=num(p),asOf=end.isoformat(),status='fresh' if (now.date()-end).days<=7 else 'stale',low52=num(lo),high52=num(hi),rangePosition=num((p-lo)/(hi-lo)*100) if hi>lo else None,belowHigh=num((p/hi-1)*100),weekChange=change(7),monthChange=change(30),macd=num(macd.iloc[-1]),signal=num(signal.iloc[-1]),histogram=num(d),histogramPrevious=num(prev),momentum='Bullish' if d>0 else ('Bearish' if d<0 else 'Neutral'),crossover=cross,rsi=num(rsi(c)),annualVolatility=num(vol),history=[dict(date=i.date().isoformat(),close=num(v)) for i,v in c.tail(180).items()],macdHistory=[dict(date=i.date().isoformat(),macd=num(macd.loc[i]),signal=num(signal.loc[i]),histogram=num(delta.loc[i])) for i in c.tail(90).index],ratings=ratings,marketCap=num(info.get('marketCap')),forwardPE=num(info.get('forwardPE')),trailingPE=num(info.get('trailingPE')),priceToSales=num(info.get('priceToSalesTrailing12Months')),revenueGrowth=num(info.get('revenueGrowth')),profitMargin=num(info.get('profitMargins')),freeCashFlow=num(info.get('freeCashflow')),totalCash=num(info.get('totalCash')),totalDebt=num(info.get('totalDebt')),targetMean=num(info.get('targetMeanPrice')),targetLow=num(info.get('targetLowPrice')),targetHigh=num(info.get('targetHighPrice')),targetCount=num(info.get('numberOfAnalystOpinions')),circulatingSupply=num(info.get('circulatingSupply')),maxSupply=num(info.get('maxSupply')),lastSuccessfulAt=now.isoformat(),fundamentalsRetrievedAt=now.isoformat(),financialPeriod=dt.datetime.fromtimestamp(info['mostRecentQuarter'],dt.timezone.utc).date().isoformat() if info.get('mostRecentQuarter') else None)
        if asset['kind']!='equity':
            for k in ['ratings','targetMean','targetLow','targetHigh','targetCount','forwardPE','trailingPE','priceToSales','revenueGrowth','profitMargin','freeCashFlow','totalCash','totalDebt']:row[k]=None
        changes=[]
        if old and old.get('price'):changes.append(f'{(p/old["price"]-1)*100:+.1f}% since last snapshot')
        if old and old.get('momentum') and old['momentum']!=row['momentum']:changes.append(f'MACD: {old["momentum"]} to {row["momentum"]}')
        if old and old.get('ratings') and ratings and abs(old['ratings']['score']-ratings['score'])>=.05:changes.append('Analyst consensus score changed')
        row['changes']=changes
        print(s,row['asOf'],row['price'],row['status'],flush=True)
    except Exception as e:
        if old and old.get('price'):
            row=dict(old);row.update(asset);row.update(status='stale',attemptedAt=now.isoformat(),refreshError='Refresh failed. Prior prices and original dates retained.')
        else:row.update(status='unavailable',price=None,asOf=None,ratings=None,refreshError='Provider did not return sufficient usable history.')
        print(s,'unavailable',str(e)[:140],flush=True)
    return row

def main():
    now=dt.datetime.now(dt.timezone.utc);old={}
    try:
        previous=ROOT/'data.json'
        if previous.exists():old=json.loads(previous.read_text())
        else:
            req=urllib.request.Request('https://raw.githubusercontent.com/Andirel/market-digest/gh-pages/seedlab/data.json',headers={'User-Agent':'SeedlabResearch/1.0'})
            with urllib.request.urlopen(req,timeout=12) as response:old=json.load(response)
    except Exception:pass
    by={a['ticker']:a for a in old.get('assets',[])+old.get('core',[])}
    rows=[]
    for a in universe()+CORE:
        rows.append(calculate(a,by.get(a['ticker']),now));time.sleep(.5)
    payload=dict(version=1,generatedAt=now.isoformat(),previousSnapshotAt=old.get('generatedAt'),assets=rows[:30],core=rows[30:],schedule='Weekly Monday morning; 12:17 UTC / 7:17 AM CDT / 6:17 AM CST',coverage=dict(total=len(rows),fresh=sum(a.get('status')=='fresh' for a in rows),stale=sum(a.get('status')=='stale' for a in rows),unavailable=sum(a.get('status')=='unavailable' for a in rows)),researchAsOf='2026-09-16',researchNotes='Prices, daily technicals and available estimates refresh weekly. Editorial theses and risk scores are dated research judgments, not automatically re-underwritten.',omitted='ARM, SE and RDDT were left out to reduce overlap and keep the research universe at 30. VTI and SGOV are additional allocation anchors.')
    text=json.dumps(payload,separators=(',',':'),allow_nan=False)
    (ROOT/'data.json').write_text(text,encoding='utf-8');(ROOT/'data.js').write_text('window.SEED_DATA='+text+';',encoding='utf-8')
    h=ROOT/'history';h.mkdir(exist_ok=True);(h/f'{now.date()}.json').write_text(text,encoding='utf-8')
    print(json.dumps(payload['coverage']))
    if not payload['coverage']['fresh']:raise SystemExit('No fresh quotes. Failure flags were saved; do not report a successful data refresh.')
if __name__=='__main__':main()
