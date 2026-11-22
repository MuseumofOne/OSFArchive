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
   if(r.archive_url!==undefined){
    const archivePath=String(r.archive_url).slice(origin.length+1);
    const allowed=r.kind==='website'?/^website\/web-[a-f0-9]{24}\.html$/.test(archivePath):r.kind==='publication'&&r.archive_url===r.url;
    if(typeof r.archive_url!=='string'||!r.archive_url.startsWith(origin+'/')||!allowed)throw new Error('Invalid archive copy destination');
   }
   if(r.original_url!==undefined){
    const original=new URL(r.original_url);
    if(typeof r.original_url!=='string'||original.origin!=='https://www.museumofone.art'||original.username||original.password||original.search||original.hash||(r.kind==='website'&&r.original_url!==r.url))throw new Error('Invalid original destination');
   }
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
 // A Ghost bundle can outlive a withdrawal. Website captures belong to live reconciliation.
 function curatedGhostSnapshot(index){
  const records=index.records.filter(record=>record.kind!=='website').map(record=>{
   const relationships=record.relationships.filter(edge=>!edge.target_id.startsWith('website:'));
   return relationships.length===record.relationships.length?record:{...record,relationships};
  });
  const counts={...index.counts};
  delete counts.website;
  return {...index,records,counts};
 }
 // A snapshot is a fallback, not proof that the remote publisher is up to date.
 // Discovery and full-text indexes use identical origin, size and schema checks.
 async function loadIndexSet(kind,config,onIndex,fetcher=globalThis.fetch){
  const origin=baseURL(config.origin),page=new URL(config.pageURL),snapshot=new URL(config.snapshot,page);
  if(snapshot.origin!==page.origin||!/^https?:$/.test(snapshot.protocol)||snapshot.username||snapshot.password)throw new Error('Research snapshot must be same-origin');
  const notify=status=>{if(typeof config.onStatus==='function')config.onStatus(status);};
  let latest,snapshotWasFiltered=false;
  try{
   const bundled=await fetchIndex(snapshot.href,origin,fetcher,{maxBytes:24*1024*1024});
   if(bundled.index_kind!==kind)throw new Error('Unexpected research index kind');
   latest=kind==='discovery'&&page.origin!==origin?curatedGhostSnapshot(bundled):bundled;
   snapshotWasFiltered=latest.records.length!==bundled.records.length||latest.records.some((record,i)=>record!==bundled.records[i]);
   onIndex(latest,'snapshot');notify('snapshot');
  }catch{latest=undefined;}
  const localPreview=['localhost','127.0.0.1','[::1]'].includes(page.hostname);
  const endpoint=origin+'/metadata/research-'+kind+'.v2.json';
  const refresh=config.remote||(!localPreview&&page.origin!==origin?endpoint:null);
  if(refresh){
   const remote=new URL(refresh);
   if(remote.href!==endpoint)throw new Error('Unexpected research refresh URL');
   try{
    const fresh=await fetchIndex(remote.href,origin,fetcher,{maxBytes:24*1024*1024});
    if(fresh.index_kind!==kind)throw new Error('Unexpected research index kind');
    if(!latest||snapshotWasFiltered||fresh.content_version!==latest.content_version){latest=fresh;onIndex(latest,'remote');}
    notify('fresh');
   }catch{notify(latest?'offline':'unavailable');}
  }else notify(latest?'snapshot-only':'unavailable');
  if(!latest)throw new Error('Research discovery unavailable');
  return latest;
 }
 function loadIndexes(config,onIndex,fetcher=globalThis.fetch){return loadIndexSet('discovery',config,onIndex,fetcher);}
 function loadPassageIndexes(config,onIndex,fetcher=globalThis.fetch){return loadIndexSet('passages',config,onIndex,fetcher);}

 // One mounted page owns one bounded refresh loop. Snapshots are loaded only
 // during initialization; a failed later request retains the last good index.
 function watchIndexSet(kind,config,onIndex,fetcher=globalThis.fetch,environment={}){
  const doc=environment.document||globalThis.document;
  const win=environment.window||doc?.defaultView||globalThis;
  const enabled=environment.enabled||(()=>true);
  const now=environment.now||(()=>Date.now());
  const interval=60000,origin=baseURL(config.origin),page=new URL(config.pageURL);
  const localPreview=['localhost','127.0.0.1','[::1]'].includes(page.hostname);
  const endpoint=origin+'/metadata/research-'+kind+'.v2.json';
  const selected=config.remote||(!localPreview?endpoint:null);
  if(selected&&new URL(selected).href!==endpoint)throw new Error('Unexpected research refresh URL');
  const visible=()=>!doc||(!doc.hidden&&doc.visibilityState!=='hidden');
  let latest,latestSource='snapshot',inFlight=null,started=false,stopped=false,lastAttempt=now();
  let resolveReady,rejectReady;
  const ready=new Promise((resolve,reject)=>{resolveReady=resolve;rejectReady=reject;});
  const alive=()=>{if(environment.connected&&!environment.connected()){stop();return false;}return !stopped;};
  const notify=value=>{if(!alive())return;if(value==='fresh')latestSource='remote';if(value==='offline'&&latestSource==='remote')value='stale';if(typeof config.onStatus==='function')config.onStatus(value);};
  const receive=(index,source)=>{if(!alive())return;latest=index;latestSource=source;onIndex(index,source,{background:false});};
  function start(){
   if(started||stopped||!visible()||!enabled())return ready;
   started=true;lastAttempt=now();
   const task=loadIndexSet(kind,{...config,onStatus:notify},receive,fetcher);
   inFlight=task;
   task.then(value=>{if(inFlight===task)inFlight=null;resolveReady(value);},error=>{if(inFlight===task)inFlight=null;rejectReady(error);});
   return ready;
  }
  function refresh(){
   if(!alive()||!visible()||!enabled())return Promise.resolve(latest);
   if(!started)return start();
   if(inFlight)return inFlight;
   if(!selected)return Promise.resolve(latest);
   lastAttempt=now();
   const task=(async()=>{
    try{
     const fresh=await fetchIndex(endpoint,origin,fetcher,{maxBytes:24*1024*1024});
     if(fresh.index_kind!==kind)throw new Error('Unexpected research index kind');
     if(!alive())return latest;
     if(!latest||fresh.content_version!==latest.content_version){latest=fresh;onIndex(latest,'remote',{background:true});}
     notify('fresh');
    }catch{notify(latest?'offline':'unavailable');}
    return latest;
   })();
   inFlight=task;
   task.then(()=>{if(inFlight===task)inFlight=null;},()=>{if(inFlight===task)inFlight=null;});
   return task;
  }
  const tick=()=>{refresh().catch(()=>{});};
  const resume=()=>{if(visible()&&(!started||now()-lastAttempt>=1000))tick();};
  const timer=selected&&typeof win.setInterval==='function'?win.setInterval(tick,interval):null;
  doc?.addEventListener('visibilitychange',resume);
  win.addEventListener?.('pageshow',resume);
  function stop(){
   if(stopped)return;stopped=true;
   if(timer!==null)win.clearInterval(timer);
   doc?.removeEventListener('visibilitychange',resume);
   win.removeEventListener?.('pageshow',resume);
  }
  start();
  return{ready,refresh,stop,get index(){return latest;}};
 }
 const controllers=new WeakMap();
 function mount(container){
  if(controllers.has(container))return controllers.get(container);
  if(container.dataset.researchDiscoveryMounted)return;
  const form=container.querySelector('[data-discovery-form]'),results=container.querySelector('[data-discovery-results]'),status=container.querySelector('[data-discovery-status]'),more=container.querySelector('[data-discovery-more]');
  if(!form||!results||!status||!container.dataset.indexSnapshot)return;
  const doc=container.ownerDocument,input=form.elements.namedItem('q'),kind=form.elements.namedItem('kind'),fulltext=form.elements.namedItem('fulltext');if(!input)return;
  container.dataset.researchDiscoveryMounted='true';let payload,passages,passageWatcher,passageFailure=false,passageStatus='',indexStatus='',shown=30,lastRenderKey='',passageWasWanted=false;
  const waitForRefresh=container.dataset.waitForRefresh==='true';
  const limitedScope=()=>waitForRefresh&&['offline','snapshot-only','unavailable'].includes(indexStatus)
   ?' Showing curated records from the bundled snapshot. Website records require the live archive.' :'';
  const params=new URLSearchParams(doc.location.search);if(params.has('q'))input.value=params.get('q');['kind','collection','year','subject','material_type','period','languages','transcription_status','source_layer'].forEach(k=>{const control=form.elements.namedItem(k);if(control&&params.has(k))control.value=params.get(k);});if(fulltext&&params.has('fulltext'))fulltext.checked=params.get('fulltext')==='1';
  const el=(tag,cls,text)=>{const node=doc.createElement(tag);if(cls)node.className=cls;if(text!==undefined)node.textContent=text;return node;};
  const destination=value=>resultURL(value,{origin:container.dataset.archiveOrigin||'https://archive.museumofone.art',pageURL:doc.location.href,localResults:container.dataset.localResults==='true'});
  const passageType=()=>!kind?.value||['publication','chapter','passage'].includes(kind.value);
  const wantsPassages=()=>Boolean(fulltext?.checked&&passageType());
  function syncPassageControls(event){if(kind?.value==='passage'&&fulltext){if(event?.target===fulltext&&!fulltext.checked)kind.value='';else fulltext.checked=true;}if(fulltext)fulltext.disabled=!passageType();}
  syncPassageControls();

  function preserveInteraction(work){
   const win=doc.defaultView,active=doc.activeElement,scope=container.closest('[data-archive-explorer]')||container;
   const row=active?.closest?.('[data-discovery-id]'),group=active?.closest?.('.ax-tree-group');
   const action=row?{id:row.dataset.discoveryId,tag:active.tagName,href:active.href||''}:null;
   const collection=group?.dataset.axCollectionGroup;
   const open=new Set(Array.from(results.querySelectorAll('[data-discovery-id] details[open]'),node=>node.closest('[data-discovery-id]').dataset.discoveryId));
   const x=win.scrollX,y=win.scrollY;
   work();
   results.querySelectorAll('[data-discovery-id]').forEach(node=>{if(open.has(node.dataset.discoveryId))node.querySelectorAll('details').forEach(details=>details.open=true);});
   if(active&&!active.isConnected){
    let target;
    if(action){const current=Array.from(results.querySelectorAll('[data-discovery-id]')).find(node=>node.dataset.discoveryId===action.id);target=current&&Array.from(current.querySelectorAll('a,summary')).find(node=>node.tagName===action.tag&&(!action.href||node.href===action.href));}
    else if(collection&&active.tagName==='SUMMARY')target=Array.from(scope.querySelectorAll('.ax-tree-group')).find(node=>node.dataset.axCollectionGroup===collection)?.querySelector('summary');
    else if(active.id)target=doc.getElementById(active.id);
    else if(active.href){const url=value=>{const next=new URL(value,doc.location.href);next.searchParams.delete('moo_shelf');return next.href;};target=Array.from(scope.querySelectorAll('a[href]')).find(node=>url(node.href)===url(active.href));}
    (target||input).focus({preventScroll:true});
   }
   if(Number.isFinite(x)&&Number.isFinite(y)&&(win.scrollX!==x||win.scrollY!==y))win.scrollTo(x,y);
  }
  function updateFacets(index){
   for(const name of ['collection','year','subject','languages','material_type','period','transcription_status']){
    const select=form.elements.namedItem(name);if(!select||select.tagName!=='SELECT')continue;
    const values=new Set();
    index.records.forEach(record=>{const value=name==='year'?String(record.date||'').slice(0,4):record[name==='subject'?'subjects':name];for(const item of (Array.isArray(value)?value:[value]))if(typeof item==='string'&&item)values.add(item);});
    const selected=select.value,old=new Map(Array.from(select.options,option=>[option.value,option]));
    if(selected)values.add(selected);
    const initial=old.get('')?.cloneNode(true)||el('option',null,'All');initial.value='';
    select.replaceChildren(initial,...[...values].sort((a,b)=>name==='year'?b.localeCompare(a):a.localeCompare(b)).map(value=>{const option=old.get(value)?.cloneNode(true)||el('option',null,value);option.value=value;return option;}));
    select.value=selected;
   }
  }
  function render(){
   if(!payload)return;
   if(waitForRefresh&&(!indexStatus||indexStatus==='snapshot')){
    status.textContent='Checking the live archive before showing search results…';return;
   }
   const filters={};['kind','collection','year','subject','material_type','period','languages','transcription_status','source_layer'].forEach(k=>{filters[k]=form.elements.namedItem(k)?.value||'';});
   if(container.dataset.searchOnly==='true'&&!normalize(input.value)&&!Object.values(filters).some(Boolean)){lastRenderKey='';results.replaceChildren();status.textContent='Search a title, name, concept or identifier across the archive.'+limitedScope();if(more)more.hidden=true;return;}
   filters.includePassages=wantsPassages();
   let pool=payload.records;if(wantsPassages()&&passages)pool=mergeIndexes([pool,passages]);
   const found=rankRecords(pool,input.value,filters);
   const renderKey=JSON.stringify([payload.content_version,wantsPassages()?passages?.content_version||'':'',input.value,filters,shown]);
   if(renderKey!==lastRenderKey){
   lastRenderKey=renderKey;results.replaceChildren();
   found.slice(0,shown).forEach(record=>{
    const type=record.kind==='entity'?(record.entity_type||'Entity'):(record.record_level||record.resource_type||record.kind);
    const item=el('li','discovery-result'),label=el('p','discovery-result-kind',[type,record.collection].filter(Boolean).join(' · ')),heading=el('h3'),link=el('a',null,record.title);
    item.dataset.discoveryId=record.id;
    const capture=record.archive_url||record.relationships?.find(edge=>edge.relation==='Stored website capture')?.url;
    link.href=destination(capture||record.url);heading.append(link);item.append(label,heading,el('p','discovery-match-reason',record.match_reason));
    if(capture||record.original_url){
     const actions=el('p','discovery-result-actions');
     for(const [label,url] of [['View archived copy',capture],['Read original',record.original_url]]){
      if(!url)continue;
      if(actions.childElementCount)actions.append(doc.createTextNode(' · '));
      const action=el('a',null,label);action.href=destination(url);actions.append(action);
     }
     item.append(actions);
    }
    if(record.source_layer)item.append(el('p','discovery-evidence','Source layer: '+(record.source_layer_label||{"research-document":"Published research document","institutional-metadata":"Institutional source metadata","primary-source":"Original archival source"}[record.source_layer]||record.source_layer)+(record.material_type?' · '+record.material_type:'')));
    if(record.summary)item.append(el('p','discovery-summary',record.summary));
    if(record.snippet)item.append(el('blockquote','discovery-snippet',record.snippet));
    if(record.reader_url){const read=el('a','discovery-reader','Read this chapter · PDF page '+record.pdf_start);read.href=destination(record.reader_url);item.append(read);}
    if(record.relationships?.length){const details=el('details','discovery-relations'),summary=el('summary',null,'Why this is connected · '+record.relationships.length+' links'),list=el('ul');details.append(summary,list);record.relationships.forEach(edge=>{const row=el('li'),a=el('a',null,edge.relation+' → '+(edge.target_title||'Related record'));a.href=destination(edge.url);row.append(a);if(edge.evidence_scope){const label={exact_edition:'Evidence matches this deposited edition',version_family:'Evidence concerns the version family',work:'Evidence concerns the work; no edition-level match asserted'}[edge.evidence_scope];if(label)row.append(el('p','discovery-evidence',label));}if(edge.note)row.append(el('p',null,edge.note));if(edge.source_url){try{const u=new URL(edge.source_url);if(u.protocol==='https:'&&!u.username&&!u.password){const source=el('a','discovery-evidence','Source evidence');source.href=destination(u.href);row.append(source);}}catch{}}list.append(row);});item.append(details);}
    if(record.kind==='passage'){const rights=record.license?.label||'See original item rights';item.append(el('p','discovery-evidence',rights+' · Extracted text; check the linked PDF for layout and wording.'));}
    results.append(item);
   });
   }
   status.textContent=found.length+' '+(found.length===1?'result':'results')+(found.length>shown?' · Showing '+shown+'.':'')+(wantsPassages()&&!passages?(passageFailure?' Passage search could not load; described records remain searchable.':' Loading source passages…'):'')+(fulltext?.checked&&!passageType()?' Source passages are outside this record type. Choose All records, Publications, Chapters or Source passages to search them.':'')+(!found.length?' Try a title, name, identifier or fewer words.':'');
   if(indexStatus==='stale')status.textContent+=' Archive update check failed; showing the last verified live index.';
   if(waitForRefresh)status.textContent+=limitedScope();
   else if(indexStatus==='offline')status.textContent+=' Live archive unavailable; showing the bundled record snapshot.';
   if(wantsPassages()&&passages&&['offline','snapshot-only'].includes(passageStatus))status.textContent+=' Passage results use the bundled snapshot; newer source text may be missing.';
   if(wantsPassages()&&passages&&passageStatus==='stale')status.textContent+=' Passage update check failed; using the last verified live source text.';
   if(more)more.hidden=found.length<=shown;
   if(container.dataset.syncUrl==='true'){const next=new URLSearchParams();if(input.value)next.set('q',input.value);Object.entries(filters).forEach(([k,v])=>{if(k!=='includePassages'&&v)next.set(k,v);});if(fulltext?.checked)next.set('fulltext','1');doc.defaultView.history.replaceState(null,'',doc.location.pathname+(next.size?'?'+next:''));}
  }
  function loadPassages(){
   const wanted=wantsPassages();
   if(!wanted){passageWasWanted=false;return;}
   if(!container.dataset.passagesUrl)return;
   if(passageWatcher){if(!passageWasWanted)passageWatcher.refresh().catch(()=>{});passageWasWanted=true;return;}
   passageWasWanted=true;
   passageWatcher=watchIndexSet('passages',{
    origin:container.dataset.archiveOrigin||'https://archive.museumofone.art',
    snapshot:container.dataset.passagesUrl,remote:container.dataset.passagesIndexUrl,
    pageURL:doc.location.href,onStatus:value=>{passageStatus=value;preserveInteraction(render);}
   },index=>{preserveInteraction(()=>{passages=index;passageFailure=false;render();});},winFetch(),{document:doc,window:doc.defaultView,enabled:wantsPassages,connected:()=>container.isConnected});
   passageWatcher.ready.catch(()=>{passageFailure=true;preserveInteraction(render);});
  }
  const winFetch=()=>doc.defaultView.fetch.bind(doc.defaultView);
  form.addEventListener('input',event=>{shown=30;syncPassageControls(event);loadPassages();render();});
  form.addEventListener('submit',event=>{if(payload){event.preventDefault();shown=30;syncPassageControls();loadPassages();render();}});
  more?.addEventListener('click',()=>{shown+=30;render();});
  status.textContent='Loading described research records…';
  const signal=(name,detail)=>container.dispatchEvent(new doc.defaultView.CustomEvent(name,{bubbles:true,detail}));
  const watcher=watchIndexSet('discovery',{
   origin:container.dataset.archiveOrigin||'https://archive.museumofone.art',snapshot:container.dataset.indexSnapshot,
   remote:container.dataset.indexUrl,pageURL:doc.location.href,
   onStatus:value=>{indexStatus=value;signal('museum:research-index-status',{status:value});preserveInteraction(render);}
  },(index,source)=>{preserveInteraction(()=>{payload=index;updateFacets(index);signal('museum:research-index',{index,source});loadPassages();render();});},winFetch(),{document:doc,window:doc.defaultView,connected:()=>container.isConnected});
  const ready=watcher.ready.catch(()=>{
   indexStatus='unavailable';
   if(payload)render();
   else status.textContent='Search is temporarily unavailable. Follow the browse links or submit your query to the archive.';
   signal('museum:research-index-status',{status:'unavailable'});
  });
  const controller={ready,render,refresh:()=>watcher.refresh(),stop:()=>{watcher.stop();passageWatcher?.stop();},get index(){return payload;},get status(){return indexStatus;}};
  controllers.set(container,controller);
  return controller;
 }
 return{normalize,baseURL,validateIndex,matches,resultURL,excerpt,rankRecords,mergeIndexes,fetchIndex,loadIndexes,loadPassageIndexes,watchIndexSet,mount};
});
