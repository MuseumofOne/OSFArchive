const test=require('node:test');
const assert=require('node:assert/strict');
const api=require('../dist/assets/research-discovery.js');
const ORIGIN='https://archive.museumofone.art';
const index=(version,records=[])=>({schema_version:2,index_kind:'discovery',canonical_origin:ORIGIN,content_version:version.repeat(64),records});
const post={id:'website:'+'a'.repeat(24),kind:'website',title:'A newly published methodology paper',url:'https://www.museumofone.art/new-methodology-paper/',archive_url:ORIGIN+'/website/web-'+ 'b'.repeat(24)+'.html',original_url:'https://www.museumofone.art/new-methodology-paper/',collection:'Methodology',summary:'An actual-shaped offline fixture for a later publication.',author:'Fixture author',date:'2026-11-22',aliases:[],identifiers:[],relationships:[],sources:[],search_text:'new methodology paper'};
const flush=async()=>{for(let i=0;i<14;i++)await Promise.resolve();};
function events(){const listeners=new Map();return{addEventListener(n,f){if(!listeners.has(n))listeners.set(n,new Set());listeners.get(n).add(f);},removeEventListener(n,f){listeners.get(n)?.delete(f);},emit(n){for(const f of listeners.get(n)||[])f();},listeners};}
for(const host of ['standalone','native'])test(host+' receives a later real-shaped post via its timer and retains it through failure',async()=>{
 let now=0,requests=0,offline=false,current=index('a'),interval;
 const doc=Object.assign(events(),{hidden:false,visibilityState:'visible'});
 const win=Object.assign(events(),{setInterval(fn,ms){assert.equal(ms,60000);interval=fn;return 1;},clearInterval(id){assert.equal(id,1);interval=null;}});
 const seen=[],status=[];
 const config={origin:ORIGIN,pageURL:host==='native'?'https://www.museumofone.art/digital-archive-library/':ORIGIN+'/',snapshot:host==='native'?'/assets/archive/research-discovery.v2.json':'/metadata/research-discovery.v2.json',onStatus:s=>status.push(s)};
 const fetcher=async()=>{requests++;if(offline)throw new Error('offline fixture');return{ok:true,headers:new Headers(),text:async()=>JSON.stringify(current)};};
 const watcher=api.watchIndexSet('discovery',config,(payload,source)=>seen.push({payload,source}),fetcher,{document:doc,window:win,now:()=>now});
 await watcher.ready;
 current=index('b',[post]);now=60000;interval();await flush();
 assert.deepEqual(seen.at(-1).payload.records,[post]);assert.equal(seen.at(-1).source,'remote');
 const unchanged=seen.length;now+=60000;interval();await flush();assert.equal(seen.length,unchanged);
 doc.hidden=true;doc.visibilityState='hidden';const paused=requests;now+=60000;interval();await flush();assert.equal(requests,paused);
 offline=true;doc.hidden=false;doc.visibilityState='visible';now+=1001;doc.emit('visibilitychange');await flush();
 assert.deepEqual(watcher.index.records,[post]);assert.equal(status.at(-1),'stale');
 offline=false;current=index('c',[{...post,summary:'Updated metadata'}]);now+=60000;interval();await flush();assert.equal(watcher.index.records[0].summary,'Updated metadata');
 watcher.stop();assert.equal(interval,null);assert.equal(doc.listeners.get('visibilitychange').size,0);assert.equal(win.listeners.get('pageshow').size,0);
});
