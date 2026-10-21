const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const html = fs.readFileSync('index.html','utf8');
const js = html.match(/<script>([\s\S]*)<\/script>/)[1];
new Function(js);
const start = js.indexOf('const HIST6');
const end = js.indexOf('function etapaStatus');
const ctx = vm.createContext({Date, console});
vm.runInContext('const SETORES_PERENES=["Bancos"];const CORES_SET={};'+js.slice(start,end),ctx);
const base = JSON.parse(fs.readFileSync('barsi-data.json'));
assert.equal(base.acoes.length,48);
assert.equal(new Set(base.acoes.map(a=>a.ticker)).size,48);
assert(!base.acoes.some(a=>a.ticker==='CPLE6'));
vm.runInContext(`ACOES=${JSON.stringify(base.acoes)}; META=${JSON.stringify(base.meta)};`,ctx);
assert(vm.runInContext('ACOES.every(a=>!veredicto(a).label.startsWith("COMPRAR"))',ctx));
vm.runInContext(`const test={...ACOES[0],setor:"Bancos",dy:8,roe:20,dividAnual:6,cotacao:100,cagrLucro:2,divEbitda:1,dyHist:Object.fromEntries(HIST6.map(y=>[y,8])),cotacaoData:new Date().toISOString(),fundamentosData:new Date().toISOString()};ACOES=[test];`,ctx);
assert.equal(vm.runInContext('ETAPAS.filter(e=>e.ok(test)).length',ctx),6);
assert.equal(vm.runInContext('veredicto(test).label',ctx),'COMPRAR');
vm.runInContext('test.cotacaoData="2020-01-01"',ctx);
assert.equal(vm.runInContext('veredicto(test).label',ctx),'AGUARDAR');
const live = js.slice(js.indexOf('const LIVE_STATE'),js.indexOf('// ─── PAINEL DE CONFIGURAÇÕES'));
Object.assign(ctx,{localStorage:{getItem:()=>null},AbortSignal,document:{getElementById:()=>null},setTimeout});
vm.runInContext(live,ctx);
(async()=>{
 for(const response of [{ok:false,status:401},{ok:false,status:429,text:async()=>''},{ok:true,json:async()=>({results:[]})}]) {
  ctx.fetch=async()=>response;
  await vm.runInContext('fetchChunk([test.ticker])',ctx);
  assert.equal(vm.runInContext('test.cotacao',ctx),100);
 }
 ctx.fetch=async()=>{throw Error('offline')};
 await vm.runInContext('fetchChunk([test.ticker])',ctx);
 assert.equal(vm.runInContext('test.cotacao',ctx),100);
 console.log('PASS: 48 tickers, regras, validade, 401, 429, vazio e offline');
})().catch(e=>{console.error(e);process.exitCode=1});
