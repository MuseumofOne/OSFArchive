/* Shared, deterministic research retrieval. No HTML from index data is executed. */
(function(root,factory){'use strict';const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else{root.MuseumResearchDiscovery=api;const start=()=>root.document.querySelectorAll('[data-research-discovery]').forEach(el=>api.mount(el));if(root.document.readyState==='loading')root.document.addEventListener('DOMContentLoaded',start,{once:true});else start();}})(typeof globalThis!=='undefined'?globalThis:this,function(){
 'use strict';
 const KINDS=new Set(['publication','chapter','entity','concept','programme','passage','website','evidence']);
 const normalize=value=>String(value||'').normalize('NFKD').replace(/[\u0300-\u036f]/g,'').replace(/[‘’]/g,"'").replace(/[–—]/g,'-').toLowerCase().replace(/\s+/g,' ').trim();
 const words=value=>normalize(value).replace(/["“”]/g,'').split(/\s+/).filter(Boolean);
 function baseURL(value){const base=String(value||'').replace(/\/$/,''),u=new URL(base);if(u.protocol!=='https:'||u.username||u.password||u.search||u.hash||u.href.replace(/\/$/,'')!==base||u.pathname.split('/').some(p=>p==='.'||p==='..'))throw new Error('Invalid discovery origin');return base;}
 function validateIndex(payload,expectedOrigin){
  const origin=baseURL(expectedOrigin);
  if(!payload||payload.schema_version!==2||payload.canonical_origin!==origin||!['discovery','passages'].includes(payload.index_kind)||!/^[a-f0-9]{64}$/.test(payload.content_version)||!Array.isArray(payload.records)||payload.records.length>20000)throw new Error('Unsupported research index');
  const ids=new Set();
  for(const r of payload.records){
   if(!r||typeof r.id!=='string'||ids.has(r.id)||!KINDS.has(r.kind)||!r.id.startsWith(r.kind+':')||typeof r.title!=='string'||typeof r.url!=='string'||typeof r.summary!=='string'||!Array.isArray(r.aliases)||!r.aliases.every(v=>typeof v==='string')||!Array.isArray(r.identifiers)||!r.identifiers.every(v=>typeof v==='string')||!Array.isArray(r.relationships)||!Array.isArray(r.sources))throw new Error('Invalid research record');
   const url=new URL(r.url);if(url.username||url.password||url.search||url.protocol!=='https:')throw new Error('Invalid research destination');
   if(r.kind==='website'){if(url.origin!=='https://www.museumofone.art'||url.hash||!/^website:[a-f0-9]{24}$/.test(r.id))throw new Error('Invalid public website destination');}
   else if(!r.url.startsWith(origin+'/')||!/^\/(?:[A-Za-z0-9._~-]+\/)*(?:items\/\d+\.html|parts\/\d+-[A-Za-z0-9_-]+\.html|entities\/[A-Za-z0-9_-]+\.html|(?:evidence|dossiers)\/[A-Za-z0-9_-]+\.html|read\/\d+\.html|vocabulary\.html|programmes\.html)$/.test(url.pathname))throw new Error('Invalid research destination');
   for(const field of ['material_type','period','transcription_status','source_layer','record_level'])if(r[field]!==undefined&&typeof r[field]!=='string')throw new Error('Invalid evidence facet');
   if(r.languages!==undefined&&(!Array.isArray(r.languages)||!r.languages.every(v=>typeof v==='string')))throw new Error('Invalid evidence languages');
   if(r.reader_url&&(typeof r.reader_url!=='string'||!r.reader_url.startsWith(origin+'/read/')||!/^\d+\.html#page=[1-9][0-9]*$/.test(r.reader_url.slice((origin+'/read/').length))))throw new Error('Invalid reader destination');
   if(r.kind==='passage'&&typeof r.text!=='string')throw new Error('Missing source passage');
   if(r.kind!=='passage'&&typeof r.search_text!=='string')throw new Error('Missing discovery text');
   if(payload.index_kind==='passages'&&r.kind!=='passage')throw new Error('Unexpected passage type');
   if(payload.index_kind==='discovery'&&r.kind==='passage')throw new Error('Unexpected discovery type');
   for(const edge of r.relationships){if(!edge||typeof edge.relation!=='string'||typeof edge.url!=='string'||!(edge.url.startsWith(origin+'/')||edge.url.startsWith('https://www.museumofone.art/'))||typeof edge.target_id!=='string')throw new Error('Invalid research relationship');const eu=new URL(edge.url);if(eu.username||eu.password||eu.protocol!=='https:')throw new Error('Invalid relationship destination');}
   ids.add(r.id);
  }
  return payload;
 }
 function matches(record,filters={}){const passageMatches=filters.includePassages===true&&record.kind==='passage'&&((filters.kind==='publication'&&record.parent_id?.startsWith('publication:'))||(filters.kind==='chapter'&&record.chapter_id?.startsWith('chapter:')));return(!filters.kind||record.kind===filters.kind||passageMatches)&&(!filters.collection||record.collection===filters.collection)&&(!filters.year||String(record.date||'').slice(0,4)===filters.year)&&(!filters.subject||(record.subjects||[]).includes(filters.subject))&&['material_type','period','transcription_status','source_layer'].every(k=>!filters[k]||record[k]===filters[k])&&(!filters.languages||(record.languages||[]).includes(filters.languages));}
 function resultURL(value,{origin,pageURL,localResults=false}={}){
  const canonical=String(value||'');if(!localResults)return canonical;
  const base=baseURL(origin);if(!canonical.startsWith(base+'/'))return canonical;
  const page=new URL(pageURL);if(!/^https?:$/.test(page.protocol)||page.username||page.password)throw new Error('Invalid local discovery page');
  const localRoot=new URL('./',page),relative=canonical.slice(base.length+1);
  if(!relative||relative.startsWith('/')||relative.startsWith('\\')||relative.includes('\\'))throw new Error('Invalid relative discovery path');
  const mapped=new URL(relative,localRoot);
  if(mapped.origin!==localRoot.origin||!mapped.pathname.startsWith(localRoot.pathname))throw new Error('Discovery destination escapes local archive root');
  return mapped.href;
 }
 function excerpt(text,query,max=280){const raw=String(text||''),needle=words(query)[0]||'',offsets=[];let folded='',at=0;for(const character of raw){const value=character.normalize('NFKD').replace(/[\u0300-\u036f]/g,'').replace(/[‘’]/g,"'").replace(/[–—]/g,'-').toLowerCase();for(const c of value){if(/\s/.test(c)){if(folded&&!folded.endsWith(' ')){folded+=' ';offsets.push(at);}}else{folded+=c;offsets.push(at);}}at+=character.length;}const found=folded.indexOf(needle),position=found<0?0:offsets[found]||0,start=Math.max(0,position-90),end=Math.min(raw.length,start+max);return(start?'…':'')+raw.slice(start,end)+(end<raw.length?'…':'');}
 function rankRecords(records,query,filters={}){
  const phrase=normalize(query).replace(/^["“]|["”]$/g,''),identifier=phrase.replace(/^(?:https?:\/\/(?:dx\.)?doi\.org\/|doi:\s*|https:\/\/orcid\.org\/)/,''),terms=words(query),quoted=/^["“].+["”]$/.test(String(query||'').trim());
  return records.filter(r=>matches(r,filters)).map(record=>{
   const title=normalize(record.title),aliases=(record.aliases||[]).map(normalize),ids=(record.identifiers||[]).map(normalize),summary=normalize(record.summary),text=normalize(record.text||record.search_text||record.searchIndex||''),all=[title,...aliases,...ids,summary,text].join(' ');
   if(phrase&&!ids.includes(identifier)&&(quoted?![title,...aliases,...ids,summary,text].some(field=>field.includes(phrase)):!terms.every(term=>all.includes(term))))return null;
   const releasedText=normalize(record.text||''),textMatches=Boolean(releasedText)&&(quoted?releasedText.includes(phrase):terms.every(term=>releasedText.includes(term)));
   let score=0,reason='Browse record';
   if(phrase){
    if(ids.includes(identifier)){score=2000;const original=(record.identifiers||[]).find(value=>normalize(value)===identifier),scope=record.identifier_scopes?.[original];reason='Exact identifier'+(scope?' · '+scope:'');}
    else if(title===phrase){score=1600;reason='Exact title or name';}
    else if(aliases.includes(phrase)){score=1500;reason='Known alternative title or name';}
    else if(title.includes(phrase)){score=1000;reason='Title or name matches';}
    else if(terms.every(t=>title.includes(t))){score=800;reason='All search terms in title or name';}
    else if(aliases.some(a=>terms.every(t=>a.includes(t)))){score=700;reason='Alternative name matches';}
    else if(summary.includes(phrase)){score=500;reason='Description matches';}
    else if(record.record_level==='Page'&&textMatches){score=350;reason='Released page text · '+(record.transcription_status||'Check reading status');}
    else if(record.kind==='passage'&&textMatches){score=300+(text.includes(phrase)?100:0);reason='Source text · PDF page '+record.page;}
    else{score=200;reason='Subjects, identifiers or connected record metadata match';}
    score+=terms.filter(t=>title.includes(t)).length*4;
   }
   return{...record,score,match_reason:reason,...(record.kind==='passage'?{snippet:excerpt(record.text,query)}:{})};
  }).filter(Boolean).sort((a,b)=>b.score-a.score||normalize(a.title).localeCompare(normalize(b.title))||String(a.id).localeCompare(String(b.id)));
 }
 function mergeIndexes(groups){const ids=new Set(),urls=new Set(),records=[];for(const group of groups){for(const r of Array.isArray(group)?group:(group?.records||[])){if(!ids.has(r.id)&&!urls.has(r.url)){ids.add(r.id);urls.add(r.url);records.push(r);}}}return records;}
 async function fetchIndex(url,origin,fetcher=globalThis.fetch,{timeout=8000,maxBytes=24*1024*1024}={}){
  const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),timeout);
  try{const response=await fetcher(url,{credentials:'omit',mode:'cors',cache:'no-cache',signal:controller.signal,headers:{Accept:'application/json'}});if(!response.ok||Number(response.headers.get('Content-Length'))>maxBytes)throw new Error('Research index unavailable');const body=await response.text();if(new TextEncoder().encode(body).length>maxBytes)throw new Error('Research index exceeds size budget');return validateIndex(JSON.parse(body),origin);}finally{clearTimeout(timer);}
 }
 async function loadIndexes(config,onIndex,fetcher=globalThis.fetch){
  const origin=baseURL(config.origin),page=new URL(config.pageURL),snapshot=new URL(config.snapshot,page);
  if(snapshot.origin!==page.origin||!/^https?:$/.test(snapshot.protocol)||snapshot.username||snapshot.password)throw new Error('Research snapshot must be same-origin');
  let latest;
  try{latest=await fetchIndex(snapshot.href,origin,fetcher,{maxBytes:24*1024*1024});if(latest.index_kind!=='discovery')throw new Error('Expected discovery index');onIndex(latest,'snapshot');}catch{latest=undefined;}
  const localPreview=['localhost','127.0.0.1','[::1]'].includes(page.hostname);
  const refresh=config.remote||(!localPreview&&page.origin!==origin?origin+'/metadata/research-discovery.v2.json':null);
  if(refresh){const remote=new URL(refresh);if(remote.href!==origin+'/metadata/research-discovery.v2.json')throw new Error('Unexpected discovery refresh URL');try{const fresh=await fetchIndex(remote.href,origin,fetcher,{maxBytes:24*1024*1024});if(fresh.index_kind!=='discovery')throw new Error('Expected discovery index');if(!latest||fresh.content_version!==latest.content_version){latest=fresh;onIndex(latest,'remote');}}catch{/* A verified bundled index remains usable. */}}
  if(!latest)throw new Error('Research discovery unavailable');return latest;
 }
 function mount(container){
  if(container.dataset.researchDiscoveryMounted)return;
  const form=container.querySelector('[data-discovery-form]'),results=container.querySelector('[data-discovery-results]'),status=container.querySelector('[data-discovery-status]'),more=container.querySelector('[data-discovery-more]');
  if(!form||!results||!status||!container.dataset.indexSnapshot)return;
  const doc=container.ownerDocument,input=form.elements.namedItem('q'),kind=form.elements.namedItem('kind'),fulltext=form.elements.namedItem('fulltext');if(!input)return;
  container.dataset.researchDiscoveryMounted='true';let payload,passages,passagesPromise,passageFailure=false,shown=30;
  const params=new URLSearchParams(doc.location.search);if(params.has('q'))input.value=params.get('q');['kind','collection','year','subject','material_type','period','languages','transcription_status','source_layer'].forEach(k=>{const control=form.elements.namedItem(k);if(control&&params.has(k))control.value=params.get(k);});if(fulltext&&params.has('fulltext'))fulltext.checked=params.get('fulltext')==='1';
  const el=(tag,cls,text)=>{const node=doc.createElement(tag);if(cls)node.className=cls;if(text!==undefined)node.textContent=text;return node;};
  const destination=value=>resultURL(value,{origin:container.dataset.archiveOrigin||'https://archive.museumofone.art',pageURL:doc.location.href,localResults:container.dataset.localResults==='true'});
  const passageType=()=>!kind?.value||['publication','chapter','passage'].includes(kind.value);
  const wantsPassages=()=>Boolean(fulltext?.checked&&passageType());
  function syncPassageControls(event){if(kind?.value==='passage'&&fulltext){if(event?.target===fulltext&&!fulltext.checked)kind.value='';else fulltext.checked=true;}if(fulltext)fulltext.disabled=!passageType();}
  syncPassageControls();
  function render(){
   if(!payload)return;
   const filters={};['kind','collection','year','subject','material_type','period','languages','transcription_status','source_layer'].forEach(k=>{filters[k]=form.elements.namedItem(k)?.value||'';});
   if(container.dataset.searchOnly==='true'&&!normalize(input.value)&&!Object.values(filters).some(Boolean)){results.replaceChildren();status.textContent='Search a title, name, concept or identifier across the archive.';if(more)more.hidden=true;return;}
   filters.includePassages=wantsPassages();
   let pool=payload.records;if(wantsPassages()&&passages)pool=mergeIndexes([pool,passages]);
   const found=rankRecords(pool,input.value,filters);results.replaceChildren();
   found.slice(0,shown).forEach(record=>{
    const item=el('li','discovery-result'),label=el('p','discovery-result-kind',record.kind==='entity'?(record.entity_type||'Entity'):(record.record_level||record.kind)),heading=el('h3'),link=el('a',null,record.title);link.href=destination(record.url);heading.append(link);item.append(label,heading,el('p','discovery-match-reason',record.match_reason));
    if(record.source_layer)item.append(el('p','discovery-evidence','Source layer: '+(record.source_layer_label||{"research-document":"Published research document","institutional-metadata":"Institutional source metadata","primary-source":"Original archival source"}[record.source_layer]||record.source_layer)+(record.material_type?' · '+record.material_type:'')));
    if(record.summary)item.append(el('p','discovery-summary',record.summary));
    if(record.snippet)item.append(el('blockquote','discovery-snippet',record.snippet));
    if(record.reader_url){const read=el('a','discovery-reader','Read this chapter · PDF page '+record.pdf_start);read.href=destination(record.reader_url);item.append(read);}
    if(record.relationships?.length){const details=el('details','discovery-relations'),summary=el('summary',null,'Why this is connected · '+record.relationships.length+' links'),list=el('ul');details.append(summary,list);record.relationships.forEach(edge=>{const row=el('li'),a=el('a',null,edge.relation+' → '+(edge.target_title||'Related record'));a.href=destination(edge.url);row.append(a);if(edge.evidence_scope){const label={exact_edition:'Evidence matches this deposited edition',version_family:'Evidence concerns the version family',work:'Evidence concerns the work; no edition-level match asserted'}[edge.evidence_scope];if(label)row.append(el('p','discovery-evidence',label));}if(edge.note)row.append(el('p',null,edge.note));if(edge.source_url){try{const u=new URL(edge.source_url);if(u.protocol==='https:'&&!u.username&&!u.password){const source=el('a','discovery-evidence','Source evidence');source.href=destination(u.href);row.append(source);}}catch{}}list.append(row);});item.append(details);}
    if(record.kind==='passage'){const rights=record.license?.label||'See original item rights';item.append(el('p','discovery-evidence',rights+' · Extracted text; check the linked PDF for layout and wording.'));}
    results.append(item);
   });
   status.textContent=found.length+' '+(found.length===1?'result':'results')+(found.length>shown?' · Showing '+shown+'.':'')+(wantsPassages()&&!passages?(passageFailure?' Passage search could not load; described records remain searchable.':' Loading source passages…'):'')+(fulltext?.checked&&!passageType()?' Source passages are outside this record type. Choose All records, Publications, Chapters or Source passages to search them.':'')+(!found.length?' Try a title, name, identifier or fewer words.':'');
   if(more)more.hidden=found.length<=shown;
   if(container.dataset.syncUrl==='true'){const next=new URLSearchParams();if(input.value)next.set('q',input.value);Object.entries(filters).forEach(([k,v])=>{if(k!=='includePassages'&&v)next.set(k,v);});if(fulltext?.checked)next.set('fulltext','1');doc.defaultView.history.replaceState(null,'',doc.location.pathname+(next.size?'?'+next:''));}
  }
  function loadPassages(){
   if(!wantsPassages()||passages||passagesPromise||!container.dataset.passagesUrl)return;
   const u=new URL(container.dataset.passagesUrl,doc.location.href),page=new URL(doc.location.href);
   if(u.origin!==page.origin){passageFailure=true;render();return;}
   passagesPromise=fetchIndex(u.href,container.dataset.archiveOrigin||'https://archive.museumofone.art').then(index=>{if(index.index_kind!=='passages')throw new Error('Expected passages');passages=index;passageFailure=false;}).catch(()=>{passageFailure=true;}).finally(()=>{passagesPromise=null;render();});
  }
  form.addEventListener('input',event=>{shown=30;syncPassageControls(event);loadPassages();render();});
  form.addEventListener('submit',event=>{if(payload){event.preventDefault();shown=30;syncPassageControls();loadPassages();render();}});
  more?.addEventListener('click',()=>{shown+=30;render();});
  status.textContent='Loading described research records…';
  const ready=loadIndexes({origin:container.dataset.archiveOrigin||'https://archive.museumofone.art',snapshot:container.dataset.indexSnapshot,remote:container.dataset.indexUrl,pageURL:doc.location.href},index=>{payload=index;loadPassages();render();}).catch(()=>{status.textContent='Search is temporarily unavailable. Follow the browse links or submit your query to the archive.';});
  return{ready,render};
 }
 return{normalize,baseURL,validateIndex,matches,resultURL,excerpt,rankRecords,mergeIndexes,fetchIndex,loadIndexes,mount};
});
