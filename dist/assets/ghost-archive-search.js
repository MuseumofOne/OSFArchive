/* Optional native Ghost entrance enhancement. Never touches Ghost global search.
 * Install only after inspecting the current theme; this file is not installed.
 * Container: [data-moo-archive-search]
 *   data-archive-origin="https://archive.museumofone.art"
 *   data-index-snapshot="{{asset 'archive/search-index.v1.json'}}" (required)
 *   data-index-url="https://archive.museumofone.art/metadata/search-index.v1.json"
 *     (optional: enable only after deployed CORS verification).
 * Inside: form[data-archive-form] with native GET action to archive catalogue,
 * input[name=q][data-archive-query], [data-archive-results] (an ol), and
 * [data-archive-status] with role=status. Optional selects use names collection,
 * year, subject, type or programme. A normal catalogue link remains in the page.
 * Bundle the generated feed at assets/archive/search-index.v1.json in the theme.
 * Uses only local index data and public HTTPS GET requests, without credentials.
 */
(function(root,factory){
 'use strict';
 const api=factory();
 if(typeof module==='object'&&module.exports)module.exports=api;
 else{
  root.MuseumArchiveSearch=api;
  const start=()=>root.document.querySelectorAll('[data-moo-archive-search]').forEach(el=>api.mount(el));
  if(root.document.readyState==='loading')root.document.addEventListener('DOMContentLoaded',start,{once:true});else start();
 }
})(typeof globalThis!=='undefined'?globalThis:this,function(){
 'use strict';
 const MAX_BYTES=1024*1024, MAX_RECORDS=5000;
 const normalize=value=>String(value||'').normalize('NFKD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
 function baseURL(value){
  if(typeof value!=='string'||/[\s\x00-\x1f]/.test(value))throw new Error('Invalid archive base URL');
  const base=value.replace(/\/$/,''),url=new URL(base);
  if(url.protocol!=='https:'||url.username||url.password||url.search||url.hash||
     url.href.replace(/\/$/,'')!==base||!/^([/][A-Za-z0-9._~-]+)*$/.test(url.pathname.replace(/\/$/,'')))throw new Error('Invalid archive base URL');
  return base;
 }
 function validateIndex(payload,expectedOrigin){
  const origin=baseURL(expectedOrigin);
  if(!payload||payload.schema_version!==1||payload.canonical_origin!==origin||
     !/^[a-f0-9]{64}$/.test(payload.content_version)||!Array.isArray(payload.records)||
     payload.records.length>MAX_RECORDS)throw new Error('Unsupported archive search index');
  const ids=new Set();
  for(const r of payload.records){
   if(!r||typeof r.id!=='string'||!(/^[1-9][0-9]*$/).test(r.id)||ids.has(r.id)||
      r.url!==origin+'/items/'+r.id+'.html'||typeof r.title!=='string'||
      typeof r.search_text!=='string'||typeof r.collection!=='string'||
      typeof r.date!=='string'||typeof r.type!=='string'||!Array.isArray(r.subjects)||
      !r.subjects.every(s=>typeof s==='string')||!Array.isArray(r.programmes)||
      !r.programmes.every(p=>p&&typeof p.id==='string'))throw new Error('Invalid archive search record');
   ids.add(r.id);
  }
  return payload;
 }
 function matches(record,filters){
  const terms=normalize(filters.q).trim().split(/\s+/).filter(Boolean);
  return terms.every(term=>normalize(record.search_text).includes(term))&&
   (!filters.collection||record.collection===filters.collection)&&
   (!filters.year||record.date.slice(0,4)===filters.year)&&
   (!filters.subject||record.subjects.includes(filters.subject))&&
   (!filters.type||record.type===filters.type)&&
   (!filters.programme||record.programmes.some(p=>p.id===filters.programme));
 }
 async function fetchIndex(url,origin,fetcher=globalThis.fetch,timeout=4000){
  const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),timeout);
  try{
   const response=await fetcher(url,{credentials:'omit',mode:'cors',cache:'no-cache',signal:controller.signal,headers:{Accept:'application/json'}});
   if(!response.ok||Number(response.headers.get('Content-Length'))>MAX_BYTES)throw new Error('Archive index unavailable');
   const body=await response.text();
   if(body.length>MAX_BYTES)throw new Error('Archive index exceeds size budget');
   return validateIndex(JSON.parse(body),origin);
  }finally{clearTimeout(timer);}
 }
 async function loadIndexes(config,onIndex,fetcher=globalThis.fetch){
  const origin=baseURL(config.origin),snapshot=new URL(config.snapshot,config.pageURL),page=new URL(config.pageURL);
  if(snapshot.origin!==page.origin||!/^https?:$/.test(snapshot.protocol)||snapshot.username||snapshot.password)throw new Error('Archive fallback must be same-origin');
  let latest;
  try{latest=await fetchIndex(snapshot.href,origin,fetcher);onIndex(latest,'snapshot');}catch{/* The native archive form remains available. */}
  if(config.remote){
   const remote=new URL(config.remote);
   if(remote.href!==origin+'/metadata/search-index.v1.json')throw new Error('Unexpected remote archive index URL');
   try{
    const current=await fetchIndex(remote.href,origin,fetcher);
    if(!latest||current.content_version!==latest.content_version){latest=current;onIndex(current,'remote');}
   }catch{/* Keep the same-origin snapshot after CORS, network or validation failure. */}
  }
  if(!latest)throw new Error('Archive search unavailable');
  return latest;
 }
 function mount(container){
  if(container.dataset.archiveSearchMounted)return;
  const form=container.querySelector('[data-archive-form]'),input=container.querySelector('[data-archive-query]'),
   results=container.querySelector('[data-archive-results]'),status=container.querySelector('[data-archive-status]');
  if(!form||!input||!results||!status||!container.dataset.indexSnapshot)return;
  container.dataset.archiveSearchMounted='true';
  const doc=container.ownerDocument;
  let payload;
  function render(){
   if(!payload)return;
   const filters={q:input.value};
   ['collection','year','subject','type','programme'].forEach(name=>{filters[name]=form.elements.namedItem(name)?.value||'';});
   const found=payload.records.filter(record=>matches(record,filters));
   results.replaceChildren();
   found.slice(0,30).forEach(record=>{
    const item=doc.createElement('li'),link=doc.createElement('a'),reference=doc.createElement('p'),description=doc.createElement('p');
    link.href=record.url;link.textContent=record.title;
    reference.textContent=[record.accession,record.author,record.date,record.type].filter(Boolean).join(' · ');
    description.textContent=record.summary||'';
    item.append(link,reference,description);results.append(item);
   });
   status.textContent=found.length+' '+(found.length===1?'archive record':'archive records')+(found.length>30?' · Showing the first 30. Refine your search or browse the catalogue.':found.length?'':'. Try another term or browse the catalogue.');
  }
  form.addEventListener('input',render);
  form.addEventListener('submit',event=>{if(payload){event.preventDefault();render();}});
  status.textContent='Loading public archive records…';
  loadIndexes({origin:container.dataset.archiveOrigin||'https://archive.museumofone.art',snapshot:container.dataset.indexSnapshot,remote:container.dataset.indexUrl,pageURL:doc.location.href},index=>{payload=index;render();})
   .catch(()=>{if(!payload)status.textContent='Archive search is temporarily unavailable. Submit your search to open the standalone catalogue.';});
 }
 return {baseURL,validateIndex,matches,fetchIndex,loadIndexes,mount};
});
