const {test}=require('node:test');
const assert=require('node:assert/strict');
const search=require('../dist/assets/ghost-archive-search.js');
const base='https://museumofone.github.io/OSFArchive';
const payload=()=>({schema_version:1,content_version:'a'.repeat(64),canonical_origin:base,records:[{
 id:'19864099',url:base+'/items/19864099.html',title:'Éthique of witnessing',author:'Dorian Vale',
 search_text:'Éthique of witnessing MOO-CAT-001 pir-prj-pyp5yx3w',collection:'Books & volumes',date:'2026-04',
 type:'Book',subjects:['Aesthetics'],programmes:[{id:'research-methods'}]
}]});
const response=data=>({ok:true,headers:{get:()=>null},text:async()=>JSON.stringify(data)});

test('consumer accepts project-path base, rejects competing destinations and schema changes',()=>{
 assert.equal(search.baseURL(base+'/'),base);
 assert.equal(search.validateIndex(payload(),base).records.length,1);
 for(const change of [p=>p.schema_version=2,p=>p.records[0].url='https://unrelated.example/',p=>p.records.push(p.records[0]),p=>p.canonical_origin='https://unrelated.example']){
  const p=payload();change(p);assert.throws(()=>search.validateIndex(p,base));
 }
 for(const invalid of ['http://archive.example','https://u:p@archive.example','https://archive.example/a/../b','https://archive.example/?q=secret'])assert.throws(()=>search.baseURL(invalid));
});

test('search preserves combined normalized terms and programme filters',()=>{
 const r=payload().records[0];
 assert.equal(search.matches(r,{q:'ethique WITNESSING',programme:'research-methods',year:'2026'}),true);
 assert.equal(search.matches(r,{q:'pir-prj-pyp5yx3w',subject:'Aesthetics'}),true);
 assert.equal(search.matches(r,{q:'ethique missing'}),false);
 assert.equal(search.matches(r,{programme:'other-programme'}),false);
});

test('CORS failure preserves the same-origin snapshot and sends no credentials',async()=>{
 const calls=[],published=[];
 const result=await search.loadIndexes({origin:base,pageURL:'https://www.museumofone.art/archive/',snapshot:'/assets/archive/search-index.v1.json',remote:base+'/metadata/search-index.v1.json'},(index,source)=>published.push(source),async(url,options)=>{
  calls.push({url,options});
  if(url.startsWith(base))throw new TypeError('Failed to fetch');
  return response(payload());
 });
 assert.equal(result.content_version,'a'.repeat(64));
 assert.deepEqual(published,['snapshot']);
 assert.equal(calls.length,2);
 assert.equal(calls[0].url,'https://www.museumofone.art/assets/archive/search-index.v1.json');
 assert.ok(calls.every(call=>call.options.credentials==='omit'));
});

test('valid fresh remote feed replaces snapshot; unsupported remote never replaces it',async()=>{
 const fresh=payload();fresh.content_version='b'.repeat(64);
 const seen=[];
 await search.loadIndexes({origin:base,pageURL:'https://www.museumofone.art/archive/',snapshot:'/assets/archive/search-index.v1.json',remote:base+'/metadata/search-index.v1.json'},(p,s)=>seen.push([p.content_version,s]),async url=>response(url.startsWith(base)?fresh:payload()));
 assert.deepEqual(seen,[['a'.repeat(64),'snapshot'],['b'.repeat(64),'remote']]);
 const bad=payload();bad.schema_version=999;
 const result=await search.loadIndexes({origin:base,pageURL:'https://www.museumofone.art/archive/',snapshot:'/assets/archive/search-index.v1.json',remote:base+'/metadata/search-index.v1.json'},()=>{},async url=>response(url.startsWith(base)?bad:payload()));
 assert.equal(result.content_version,'a'.repeat(64));
});

test('fallback must be same-origin, both failures reject and oversized bodies reject',async()=>{
 await assert.rejects(search.loadIndexes({origin:base,pageURL:'https://www.museumofone.art/archive/',snapshot:'https://unrelated.example/index.json'},()=>{}));
 await assert.rejects(search.loadIndexes({origin:base,pageURL:'https://www.museumofone.art/archive/',snapshot:'/assets/archive/search-index.v1.json'},()=>{},async()=>{throw new Error('offline');}));
 await assert.rejects(search.fetchIndex(base+'/metadata/search-index.v1.json',base,async()=>({ok:true,headers:{get:()=>2*1024*1024},text:async()=>''})));
});
