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
let checks=0;
for(const [name,p] of Object.entries(PRESETS)){
 for(const budget of [1000,99999.99,100000,1000000])for(const maxpos of [3,5,8,12])for(const horizon of [3,5,7,10,15])for(const crypto of [true,false]){
  const s={...DEFAULT,...p,preset:name,budget,maxpos,horizon,crypto,beliefs:{...p.beliefs},excluded:[]};
  const m=model(data,s);
  assert(Math.abs(m.holdings.reduce((n,a)=>n+a.amount,0)-budget)<.015,'Total budget');
  m.holdings.forEach(a=>{assert(Number.isFinite(a.amount)&&a.amount>=0);if(!['VTI','SGOV'].includes(a.ticker))assert(a.amount<=budget*maxpos/100+.01,'Asset cap');});
  for(const [theme,v] of Object.entries(m.totals))if(!['core','reserve'].includes(theme))assert(v<=budget*.35+.02,'Theme cap');
  assert((m.totals.crypto||0)<=m.cryptoLimit+.02,'Token cap');
  if(!crypto)assert(!m.holdings.some(a=>a.kind==='crypto'),'Crypto opt-out');
  if(horizon<5)assert(m.allocations.SGOV===budget,'Short horizon');
  assert(!m.holdings.some(a=>a.ticker==='LINK'),'Existing LINK opt-out');
  checks++;
 }
}
// Generic oversized existing exposure, not a user's holdings.
const s={...DEFAULT,preset:'aggressive',...PRESETS.aggressive,beliefs:{...PRESETS.aggressive.beliefs},budget:100000,linkUnits:1000000,excluded:[]};
const m=model(data,s);assert(m.cryptoLimit===0,'Existing crypto cap');assert(!m.holdings.some(a=>a.kind==='crypto'));
const empty={...s,beliefs:{ai:0,power:0,space:0,finance:0,health:0,crypto:0}};const e=model(data,empty);assert(e.holdings.every(a=>['VTI','SGOV'].includes(a.ticker)));
for(const a of data.assets.concat(data.core)){
 if(a.status==='fresh'){
  assert(a.price>0&&a.rsi>=0&&a.rsi<=100,'Market bounds '+a.ticker);
  assert(a.low52<=a.price+.0001&&a.high52>=a.price-.0001,'Range '+a.ticker);
  assert(Math.abs(a.histogram-(a.macd-a.signal))<.000003,'MACD '+a.ticker);
 }
 if(a.kind!=='equity')assert(!a.ratings,'No synthetic crypto or ETF analyst consensus');
}
console.log('PASS: '+checks+' allocation combinations; budget, caps, themes, crypto opt-out, existing exposure, short horizons, and data invariants.');
