'use strict';
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const app=fs.readFileSync(__dirname+'/app.js','utf8');
const marker='window.SeedlabModel={model,weightedCap,PRESETS,DEFAULT};';
assert(app.includes(marker),'Allocation test interface is absent');
const data=JSON.parse(fs.readFileSync(__dirname+'/data.json','utf8'));
const context={window:{SEED_DATA:data},document:{getElementById:()=>null},localStorage:{getItem:()=>null},console,Date};
vm.createContext(context);vm.runInContext(app.slice(0,app.indexOf(marker)+marker.length),context);
const {model,PRESETS,DEFAULT}=context.window.SeedlabModel;
assert(data.assets.length===30);assert(new Set(data.assets.map(a=>a.ticker)).size===30);
assert(DEFAULT.excluded.length===0,'General defaults must not exclude any asset');
assert(DEFAULT.existingCrypto===0,'No existing holdings may be assumed');
let checks=0;
function verify(m,s){
 assert(Math.abs(m.holdings.reduce((n,a)=>n+a.amount,0)-s.budget)<.005,'Total budget');
 m.holdings.forEach(a=>{assert(Number.isFinite(a.amount)&&a.amount>=0);if(!['VTI','SGOV'].includes(a.ticker))assert(a.amount<=s.budget*s.maxpos/100+.00001,'Asset cap');});
 for(const [theme,v] of Object.entries(m.totals))if(!['core','reserve'].includes(theme))assert(v<=s.budget*.35+.00001,'Theme cap');
 assert((m.totals.crypto||0)<=m.cryptoLimit+.00001,'Token cap');
 if(!s.crypto)assert(!m.holdings.some(a=>a.kind==='crypto'),'Crypto opt-out');
 if(s.horizon<5)assert(m.allocations.SGOV===s.budget,'Short horizon');
 for(const a of m.holdings)assert(!s.excluded.includes(a.ticker),'Generic asset exclusions');
}
for(const [name,p] of Object.entries(PRESETS)){
 for(const budget of [1000,99999.99,100000,1000000])for(const maxpos of [3,5,8,12])for(const horizon of [3,5,7,10,15])for(const crypto of [true,false]){
  const s={...DEFAULT,...p,preset:name,budget,maxpos,horizon,crypto,beliefs:{...p.beliefs},excluded:[]};
  verify(model(data,s),s);checks++;
 }
}
// Generic values; these are not any user's holdings.
const s={...DEFAULT,...PRESETS.aggressive,preset:'aggressive',beliefs:{...PRESETS.aggressive.beliefs},budget:100000,existingCrypto:1000000,excluded:[]};
const m=model(data,s);assert(m.cryptoLimit===0,'Existing crypto cap');assert(!m.holdings.some(a=>a.kind==='crypto'));
const empty={...s,beliefs:{ai:0,power:0,space:0,finance:0,health:0,crypto:0}};const e=model(data,empty);assert(e.holdings.every(a=>['VTI','SGOV'].includes(a.ticker)));
for(const budget of [1,10.25,250,25000,75000.55,100000000])for(const [name,p]of Object.entries(PRESETS)){
 const a={...DEFAULT,...p,preset:name,budget,beliefs:{...p.beliefs},excluded:[]};verify(model(data,a),a);
}
for(const budget of ['',0,-1,Infinity,NaN,100000001,5.555])assert.throws(()=>model(data,{...DEFAULT,budget}),'Invalid budgets must not silently become $100,000');
const generic={...DEFAULT,...PRESETS.balanced,preset:'balanced',beliefs:{...PRESETS.balanced.beliefs},excluded:[]};
for(const asset of data.assets){const a={...generic,excluded:[asset.ticker]};verify(model(data,a),a)}
const base=model(data,{...generic,budget:25000});const larger=model(data,{...generic,budget:100000});
for(const a of base.holdings)assert(Math.abs(a.amount*4-(larger.allocations[a.ticker]||0))<1,'Allocations scale with custom investment size');
for(const a of data.assets.concat(data.core)){
 if(a.status==='fresh'){
  assert(a.price>0&&a.rsi>=0&&a.rsi<=100,'Market bounds '+a.ticker);
  assert(a.low52<=a.price+.0001&&a.high52>=a.price-.0001,'Range '+a.ticker);
  assert(Math.abs(a.histogram-(a.macd-a.signal))<.000003,'MACD '+a.ticker);
 }
 if(a.kind!=='equity')assert(!a.ratings,'No synthetic crypto or ETF analyst consensus');
}
const html=fs.readFileSync(__dirname+'/index.html','utf8');
assert(html.indexOf('id="budget"')<html.indexOf('id="controls"'),'Investment size must be visible outside collapsed mobile controls');
assert((html.match(/id="budget"/g)||[]).length===1,'Single source of truth for capital');
assert(!/LINK units|additional LINK|avoidLink|linkUnits/.test(html+app),'No asset-specific portfolio controls');
console.log('PASS: '+checks+' allocation combinations; custom amounts, invalid input, generic exclusions, no assumed holdings, and data invariants.');
