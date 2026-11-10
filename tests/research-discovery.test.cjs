const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const api = require('../dist/assets/research-discovery.js');
const origin = 'https://archive.museumofone.art';
const root = path.resolve(__dirname, '..');
const load = name => JSON.parse(fs.readFileSync(path.join(root, name), 'utf8'));
const response = payload => ({ok: true, headers: {get: () => null}, text: async () => JSON.stringify(payload)});
const fixture = () => ({schema_version: 2, index_kind: 'discovery', canonical_origin: origin, content_version: 'a'.repeat(64), records: [{id: 'publication:123', kind: 'publication', title: 'Exact witness', url: origin + '/items/123.html', summary: 'Source description', aliases: ['Witness alternative'], identifiers: ['10.1234/example'], relationships: [], sources: [{url: 'https://zenodo.org/records/123'}], search_text: 'Exact witness proof evidence'}]});

test('exact identifiers, titles, aliases and explanations outrank metadata noise', () => {
 const exact=fixture().records[0], noise={...exact,id:'publication:124',url:origin+'/items/124.html',title:'Other',aliases:[],identifiers:[],search_text:'Exact witness Witness alternative 10.1234/example'};
 for(const q of ['Exact witness','Witness alternative','10.1234/example','https://doi.org/10.1234/example']){
  const result=api.rankRecords([noise,exact],q); assert.equal(result[0].id,exact.id);assert.ok(result[0].match_reason);
 }
 assert.equal(api.rankRecords([exact],'unrepresented word').length,0);
 assert.equal(api.rankRecords([exact],'witness',{kind:'chapter'}).length,0);
});
test('source snippets are literal slices with explicit truncation',()=>{
 const text='Opening words. Evidence is on this page. Closing words.';
 assert.equal(api.excerpt(text,'evidence'),text);
 const long='x'.repeat(300)+' evidence '+'z'.repeat(300),snippet=api.excerpt(long,'evidence');
 assert.ok(long.includes(snippet.replace(/^…|…$/g,'')));assert.ok(snippet.includes('evidence'));
});
test('standalone destinations follow localhost or project roots while canonical and website links stay intact',()=>{
 const canonical=origin+'/read/19864099.html#page=9';
 assert.equal(api.resultURL(canonical,{origin,pageURL:'http://127.0.0.1:8000/research-discovery.html?q=proof',localResults:true}),'http://127.0.0.1:8000/read/19864099.html#page=9');
 assert.equal(api.resultURL(origin+'/parts/19864099-c002.html',{origin,pageURL:'https://museumofone.github.io/OSFArchive/research-discovery.html',localResults:true}),'https://museumofone.github.io/OSFArchive/parts/19864099-c002.html');
 assert.equal(api.resultURL(origin+'/assets/documents/19864099.pdf#page=9',{origin,pageURL:'http://localhost:8000/preview/research-discovery.html',localResults:true}),'http://localhost:8000/preview/assets/documents/19864099.pdf#page=9');
 assert.equal(api.resultURL(canonical,{origin,pageURL:'https://www.museumofone.art/digital-archive-library/',localResults:false}),canonical);
 const website='https://www.museumofone.art/answerability/';assert.equal(api.resultURL(website,{origin,pageURL:'http://localhost:8000/research-discovery.html',localResults:true}),website);
 assert.equal(api.resultURL(origin+'/entities/dorian-vale.html#entity',{origin,pageURL:'https://archive.museumofone.art/research-discovery.html',localResults:true}),origin+'/entities/dorian-vale.html#entity');
 assert.throws(()=>api.resultURL(origin+'/../outside',{origin,pageURL:'http://localhost:8000/project/research-discovery.html',localResults:true}),/escapes/);
});
test('passage search respects publication and checked chapter containment filters',()=>{
 const publication=fixture().records[0],passage={...publication,id:'passage:123:4',kind:'passage',url:origin+'/read/123.html#page=4',title:'Page 4',text:'Source proof is here.',parent_id:publication.id,chapter_id:'chapter:123:c001',page:4},outside={...passage,id:'passage:123:1',chapter_id:undefined};
 const rows=[publication,passage,outside];
 assert.deepEqual(api.rankRecords(rows,'proof',{kind:'publication'}).map(r=>r.id),[publication.id]);
 assert.equal(api.rankRecords(rows,'proof',{kind:'publication',includePassages:true}).length,3);
 assert.deepEqual(api.rankRecords(rows,'proof',{kind:'chapter',includePassages:true}).map(r=>r.id),[passage.id]);
 assert.equal(api.rankRecords(rows,'proof',{kind:'entity',includePassages:true}).length,0);
 assert.equal(api.rankRecords(rows,'proof',{kind:'passage'}).length,2);
});
test('reject cross-origin results, malicious reader URLs, schema drift and duplicates',()=>{
 for(const mutate of [p=>p.records[0].url='https://elsewhere.example/items/123.html',p=>p.records[0].reader_url='javascript:alert(1)',p=>p.schema_version=99,p=>p.records.push(p.records[0])]){
  const p=fixture();mutate(p);assert.throws(()=>api.validateIndex(p,origin));
 }
 assert.equal(api.validateIndex(fixture(),origin).records.length,1);
});
test('offline remote retains bundled snapshot without credentials',async()=>{
 const seen=[],calls=[];const fetcher=async(url,options)=>{calls.push({url,options});if(url.includes('/assets/'))return response(fixture());throw new Error('Offline');};
 const got=await api.loadIndexes({origin,pageURL:'https://www.museumofone.art/digital-archive-library/',snapshot:'/assets/archive/research-discovery.v2.json',remote:origin+'/metadata/research-discovery.v2.json'},(p,source)=>seen.push(source),fetcher);
 assert.equal(got.content_version,'a'.repeat(64));assert.deepEqual(seen,['snapshot']);assert.ok(calls.every(c=>c.options.credentials==='omit'));
});
test('remote refresh replaces snapshot and both failures reject to native fallback',async()=>{
 const fresh=fixture();fresh.content_version='b'.repeat(64);const seen=[];
 const config={origin,pageURL:'https://www.museumofone.art/',snapshot:'/assets/index.json',remote:origin+'/metadata/research-discovery.v2.json'};
 const result=await api.loadIndexes(config,(p,s)=>seen.push(s),async u=>response(u.includes('/assets/')?fixture():fresh));
 assert.deepEqual(seen,['snapshot','remote']);assert.equal(result.content_version,fresh.content_version);
 await assert.rejects(api.loadIndexes(config,()=>{},async()=>{throw new Error('Offline');}));
 await assert.rejects(api.loadIndexes({...config,snapshot:'https://evil.example/index.json'},()=>{},async()=>response(fixture())));
});
test('native explorer and global search configurations refresh website captures without an explicit remote field',async()=>{
 const fresh=fixture();fresh.content_version='c'.repeat(64);fresh.records.push({...fresh.records[0],id:'website:'+'1'.repeat(24),kind:'website',title:'Encounter Differential',url:'https://www.museumofone.art/encounter-differential/',search_text:'Encounter Differential public tool guide',relationships:[{relation:'Stored website capture',target_id:'capture:tool',url:origin+'/website/web-'+'1'.repeat(24)+'.html'}]});
 const seen=[],calls=[];
 const got=await api.loadIndexes({origin,pageURL:'https://www.museumofone.art/digital-archive-library/',snapshot:'/assets/archive/research-discovery.v2.json'},(p,s)=>seen.push(s),async u=>{calls.push(u);return response(u.includes('/assets/')?fixture():fresh);});
 assert.deepEqual(seen,['snapshot','remote']);assert.equal(calls[1],origin+'/metadata/research-discovery.v2.json');assert.equal(api.rankRecords(got.records,'Encounter Differential')[0].kind,'website');
 const localCalls=[];await api.loadIndexes({origin,pageURL:origin+'/',snapshot:'/metadata/research-discovery.v2.json'},()=>{},async u=>{localCalls.push(u);return response(fresh);});assert.equal(localCalls.length,1);
});
test('malformed or oversized index does not replace valid snapshot',async()=>{
 const seen=[];const config={origin,pageURL:'https://www.museumofone.art/',snapshot:'/assets/index.json',remote:origin+'/metadata/research-discovery.v2.json'};
 await api.loadIndexes(config,(p,s)=>seen.push(s),async url=>url.includes('/assets/')?response(fixture()):{ok:true,headers:{get:()=>9000000},text:async()=>''});
 assert.deepEqual(seen,['snapshot']);
});
test('forty real corpus retrieval cases meet the declared target ranks',()=>{
 const feed=load('dist/metadata/research-discovery.v2.json'),passages=load('dist/metadata/research-passages.v2.json');
 api.validateIndex(feed,origin);api.validateIndex(passages,origin);
 const benchmark=load('data/discovery-benchmark.json');assert.equal(benchmark.queries.length,40);
 for(const example of benchmark.queries){const pool=example.fulltext?api.mergeIndexes([feed,passages]):feed.records;const results=api.rankRecords(pool,example.query,example.filters||{});const rank=results.findIndex(r=>r.id===example.expected_id)+1;assert.ok(rank>0&&rank<=example.max_rank,`${example.label}: expected ${example.expected_id} in top ${example.max_rank}, got ${results.slice(0,5).map(r=>r.id).join(', ')}`);}
});


test('contextual name variants retrieve the person while dialogue status stays explicit',()=>{
 const feed=load('dist/metadata/research-discovery.v2.json');
 for(const [query,id] of [['Kazuo Shiraga','shiraga-kazuo'],['Shiraga Kazuo','shiraga-kazuo'],['Dong-Yeon Koh','dong-yeon-koh'],['Koh Dongyeon','dong-yeon-koh'],['Reiko Tomii','reiko-tomii'],['Paul Gladston','paul-gladston']]){
  assert.equal(api.rankRecords(feed.records,query,{kind:'entity'})[0].id,'entity:'+id);
 }
 const gladston=feed.records.find(r=>r.id==='entity:paul-gladston');
 assert.match(gladston.summary,/unpublished/);
 assert.ok(gladston.relationships.some(r=>r.relation==='dialogue participation documented in'));
 assert.ok(!gladston.relationships.some(r=>/author|employee|member|publisher/.test(r.relation)));
});


test('localhost preview retains the staged feed without replacing it from production',async()=>{
 const calls=[];
 await api.loadIndexes({origin,pageURL:'http://127.0.0.1:8846/research-discovery.html',snapshot:'/metadata/research-discovery.v2.json'},()=>{},async u=>{calls.push(u);return response(fixture());});
 assert.deepEqual(calls,['http://127.0.0.1:8846/metadata/research-discovery.v2.json']);
});

test('evidence facets combine without hiding the distinction between source and research',()=>{
 const feed=load('dist/metadata/research-discovery.v2.json');api.validateIndex(feed,origin);
 const results=api.rankRecords(feed.records,'Park',{kind:'evidence',source_layer:'research-document',material_type:'published-paper',languages:'ko'});
 assert.ok(results.length>=1);assert.ok(results.every(r=>r.source_layer==='research-document'&&r.languages.includes('ko')));
 const sources=api.rankRecords(feed.records,'1974',{kind:'evidence',source_layer:'institutional-source',transcription_status:'not-reproduced'});
 assert.ok(sources.some(r=>r.id==='evidence:mmca-2016-report-entry-76'));
 for(const field of ['material_type','period','source_layer']){const bad=structuredClone(feed);bad.records[0][field]={value:'invalid'};assert.throws(()=>api.validateIndex(bad,origin));}
});

test('released text reasons exclude metadata-only and mixed-field matches',()=>{
 for(const kind of ['evidence','passage']){
  const record={...fixture().records[0],id:kind+':scope-check',kind,record_level:'Page',title:'Park documentary record',aliases:['acquisition'],identifiers:[],summary:'A described research source',text:'The released wording describes wood.',page:4,transcription_status:'Reviewed extraction'};
  for(const query of ['Park acquisition','Park wood']){
   const result=api.rankRecords([record],query);assert.equal(result.length,1);
   assert.equal(result[0].match_reason,'Subjects, identifiers or connected record metadata match');
  }
 }
});

test('released text reasons require every unquoted term in the actual text',()=>{
 for(const [kind,record_level,expected] of [['evidence','Page','Released page text'],['passage',undefined,'Source text']]){
  const record={...fixture().records[0],id:kind+':text-check',kind,record_level,title:'Documentary record',aliases:[],identifiers:[],summary:'A described research source',text:'Wood is described before the acquisition entry.',page:4,transcription_status:'Reviewed extraction'};
  const result=api.rankRecords([record],'wood acquisition');assert.equal(result.length,1);assert.ok(result[0].match_reason.startsWith(expected));
 }
});

test('quoted released text requires a contiguous normalized phrase',()=>{
 for(const [kind,record_level,expected] of [['evidence','Page','Released page text'],['passage',undefined,'Source text']]){
  const record={...fixture().records[0],id:kind+':phrase-check',kind,record_level,title:'Documentary record',aliases:[],identifiers:[],summary:'A described research source',text:'Wood and acquisition are separately described.',page:4,transcription_status:'Reviewed extraction'};
  assert.equal(api.rankRecords([record],'"wood acquisition"').length,0);
  const exact=api.rankRecords([{...record,text:'The WOOD   acquisition is described.'}],'"wood acquisition"');assert.equal(exact.length,1);assert.ok(exact[0].match_reason.startsWith(expected));
  const alias=api.rankRecords([{...record,aliases:['wood acquisition']}],'"wood acquisition"');assert.equal(alias.length,1);assert.equal(alias[0].match_reason,'Known alternative title or name');
 }
});
