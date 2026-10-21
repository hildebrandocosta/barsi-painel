const fs=require('node:fs');
const vm=require('node:vm');
const assert=require('node:assert/strict');
const html=fs.readFileSync('index.html','utf8');
const code=html.match(/<script>([\s\S]*)<\/script>/)[1];
const base=JSON.parse(fs.readFileSync('barsi-data.json'));
const storage=new Map();
const element=()=>({style:{setProperty(){}},dataset:{},value:'',textContent:'',innerHTML:'',appendChild(){},addEventListener(){},querySelectorAll(){return []},classList:{toggle(){},add(){},remove(){}}});
const nodes=new Map();
const document={addEventListener(){},createElement:element,querySelectorAll:()=>[],querySelector:()=>element(),getElementById(id){if(!nodes.has(id))nodes.set(id,element());return nodes.get(id)}};
const ctx=vm.createContext({document,window:{},localStorage:{getItem:k=>storage.get(k)||null,setItem:(k,v)=>storage.set(k,v)},console,setTimeout:()=>{},Date,AbortSignal,fetch:async()=>({ok:true,json:async()=>structuredClone(base)})});
vm.runInContext(code,ctx);
(async()=>{
 assert(await vm.runInContext('carregarDados()',ctx));
 vm.runInContext(`for (const a of ACOES) {
   for (const render of [renderAbaAnalise,renderAbaIndicadores,renderAbaGraficos,renderAbaResumo,renderAbaRecomendacoes]) {
     const out=render(a);
     if(typeof out !== 'string' || out.includes('NaN') || out.includes('Infinity')) throw Error('Render inválido: '+a.ticker);
   }
 }`,ctx);
 vm.runInContext('renderAll()',ctx);
 const good=storage.get('barsi_data_cache');
 ctx.fetch=async()=>{throw Error('offline')};
 assert(await vm.runInContext('carregarDados()',ctx));
 assert.equal(vm.runInContext('ACOES.length',ctx),48);
 ctx.fetch=async()=>({ok:true,json:async()=>({acoes:[{ticker:'BAD'}]})});
 assert(await vm.runInContext('carregarDados()',ctx));
 assert.equal(storage.get('barsi_data_cache'),good);
 storage.delete('barsi_data_cache');
 assert.equal(await vm.runInContext('carregarDados()',ctx),false);
 console.log('PASS: 240 renderizações, lista, cache offline e rejeição de base inválida; Chart.js ausente');
})().catch(e=>{console.error(e);process.exitCode=1});
