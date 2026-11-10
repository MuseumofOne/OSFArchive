/* One native explorer controller, scoped to its root in either host. */
(function(root,factory){'use strict';const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else{root.ArchiveExplorer=api;const start=()=>root.document.querySelectorAll('[data-archive-explorer]').forEach(node=>api.mount(node));if(root.document.readyState==='loading')root.document.addEventListener('DOMContentLoaded',start,{once:true});else start();}})(typeof globalThis!=='undefined'?globalThis:this,function(){
'use strict';
const STORAGE='museum-of-one-reading-list-v1',VIEWS=new Set(['overview','catalogue','discover','reading']);
function shelfIds(raw){if(typeof raw!=='string'||raw.length>2000||!/^\d+(?:,\d+)*$/.test(raw))return[];return[...new Set(raw.split(','))].slice(0,200);}
function handoffURL(value,saved,origin,pageURL){const u=new URL(value,pageURL);if(u.origin!==new URL(origin).origin||u.protocol!=='https:')return u.href;const ids=shelfIds(saved.join(','));if(ids.length)u.searchParams.set('moo_shelf',ids.join(','));else u.searchParams.delete('moo_shelf');return u.href;}
function readState(hash){if(hash==='#public-catalogue')hash='#ax:view=catalogue';if(!String(hash).startsWith('#ax:'))return{view:'overview',collection:'',q:'',year:'',type:'',sort:'newest',layout:'shelf',dq:'',dk:'',fulltext:false};const p=new URLSearchParams(hash.slice(4));return{view:VIEWS.has(p.get('view'))?p.get('view'):'overview',collection:p.get('collection')||'',q:p.get('q')||'',year:p.get('year')||'',type:p.get('type')||'',sort:['reference','oldest','title'].includes(p.get('sort'))?p.get('sort'):'newest',layout:p.get('layout')==='list'?'list':'shelf',dq:p.get('dq')||'',dk:p.get('dk')||'',fulltext:p.get('fulltext')==='1'};}
function stateHash(state){const p=new URLSearchParams();p.set('view',VIEWS.has(state.view)?state.view:'overview');for(const key of ['collection','q','year','type','dq','dk'])if(state[key])p.set(key,state[key]);if(state.sort&&state.sort!=='newest')p.set('sort',state.sort);if(state.layout==='list')p.set('layout','list');if(state.fulltext)p.set('fulltext','1');return'#ax:'+p;}
function mount(root){
 if(root.dataset.axMounted)return;
 const doc=root.ownerDocument,win=doc.defaultView,core=win.ArchiveCore;
 if(!core)return;
 let records;try{records=JSON.parse(root.querySelector('[data-ax-records]').textContent);if(!Array.isArray(records)||!records.every(r=>/^\d+$/.test(r.id)&&typeof r.title==='string')||new Set(records.map(r=>r.id)).size!==records.length)throw new Error();}catch{return;}
 root.dataset.axMounted='true';root.classList.add('ax-enhanced');
 const tree=root.querySelector('.ax-tree>details'),narrow=win.matchMedia('(max-width:1100px)');tree.open=!narrow.matches;narrow.addEventListener('change',event=>tree.open=!event.matches);
 const $=selector=>root.querySelector(selector),$$=selector=>Array.from(root.querySelectorAll(selector));
 const byId=new Map(records.map(r=>[r.id,r])),knownIds=new Set(byId.keys());
 let saved=[],storageOK=true,selected=new Set(),expanded=false,previousOverflow='',inertElements=[];
 try{saved=core.parseSaved(win.localStorage.getItem(STORAGE));}catch{storageOK=false;}
 const incoming=new URL(win.location.href),carry=shelfIds(incoming.searchParams.get('moo_shelf'));
 if(carry.length){saved=[...new Set([...saved,...carry.filter(id=>knownIds.has(id))])].slice(0,200);try{win.localStorage.setItem(STORAGE,JSON.stringify(saved));}catch{storageOK=false;}incoming.searchParams.delete('moo_shelf');win.history.replaceState(null,'',incoming.pathname+incoming.search+incoming.hash);}
 let state=readState(win.location.hash);if(win.location.hash==='#archive-search')state.view='discover';
 const filter=$('[data-ax-filter]'),grid=$('[data-ax-cards]'),cards=Array.from(grid.children),message=$('[data-ax-message]');
 const make=(tag,cls,text)=>{const n=doc.createElement(tag);if(cls)n.className=cls;if(text!==undefined)n.textContent=text;return n;};
 const announce=text=>{message.textContent=text;};
 function href(path){return root.dataset.standalone==='true'?path:root.dataset.origin+'/'+path;}
 function sync(){
  $$('[data-ax-count]').forEach(n=>n.textContent=saved.length);
  $$('[data-ax-save]').forEach(n=>{const active=saved.includes(n.dataset.axSave);n.setAttribute('aria-pressed',String(active));n.textContent=active?'✓ Saved':'＋ Save';});
 }
 function persist(){try{win.localStorage.setItem(STORAGE,JSON.stringify(saved));}catch{storageOK=false;}sync();win.dispatchEvent(new win.CustomEvent('moo-reading-list-change',{detail:saved.slice()}));}
 function setHash(push=false){const next=win.location.pathname+win.location.search+stateHash(state);win.history[push?'pushState':'replaceState'](null,'',next);}
 function filters(){for(const key of ['q','collection','year','type','sort']){const field=filter.elements.namedItem(key);field.value=state[key]||'';if(field.value!==(state[key]||''))state[key]=field.value;}
  let count=0;cards.forEach(card=>{const data={search:card.dataset.search,group:card.dataset.collection,year:card.dataset.year,type:card.dataset.type};card.hidden=!core.matches(data,state);if(!card.hidden)count++;});
  [...cards].sort((a,b)=>state.sort==='title'?a.dataset.title.localeCompare(b.dataset.title):state.sort==='newest'?b.dataset.date.localeCompare(a.dataset.date):state.sort==='oldest'?a.dataset.date.localeCompare(b.dataset.date):records.findIndex(r=>r.id===a.dataset.axRecord)-records.findIndex(r=>r.id===b.dataset.axRecord)).forEach(card=>grid.append(card));
  grid.dataset.layout=state.layout;$$('[data-ax-layout]').forEach(n=>n.setAttribute('aria-pressed',String(n.dataset.axLayout===state.layout)));$('[data-ax-results]').textContent=count+' '+(count===1?'record':'records');$('[data-ax-empty]').hidden=count!==0;
 }
 function show(view,{push=false,focus=false}={}){
  state.view=VIEWS.has(view)?view:'overview';$$('[data-ax-panel]').forEach(panel=>panel.hidden=panel.dataset.axPanel!==state.view);$$('[data-ax-view]').forEach(link=>{if(link.dataset.axView===state.view)link.setAttribute('aria-current','page');else link.removeAttribute('aria-current');});
  if(state.view==='catalogue')filters();if(state.view==='reading')renderReading();if(state.view==='discover'){const form=$('[data-discovery-form]');form.elements.namedItem('q').value=state.dq||'';form.elements.namedItem('kind').value=state.dk||'';form.elements.namedItem('fulltext').checked=Boolean(state.fulltext);win.MuseumResearchDiscovery?.mount($('[data-research-discovery]'));form.dispatchEvent(new win.Event('input',{bubbles:true}));}
  setHash(push);if(focus){const panel=$('[data-ax-panel="'+state.view+'"]'),target=panel.querySelector('input,select,h3');if(target){if(target.tagName==='H3')target.tabIndex=-1;target.focus({preventScroll:true});panel.scrollIntoView({behavior:'auto',block:'start'});}}
 }
 function updateReadingCompare(){const button=$('[data-ax-compare]');button.disabled=selected.size<2||selected.size>3;button.textContent=selected.size?'Compare '+selected.size+' selected records':'Compare selected records';}
 function renderReading(){
  const host=$('[data-ax-reading]');host.replaceChildren();selected=new Set([...selected].filter(id=>saved.includes(id)&&byId.has(id)));const known=saved.map(id=>byId.get(id)).filter(Boolean);
  if(!known.length)host.append(make('p','ax-note','Use Save on a catalogue record to build your reading list.'));
  known.forEach(record=>{const article=make('article','ax-reading-entry'),label=make('label'),check=make('input');check.type='checkbox';check.checked=selected.has(record.id);check.setAttribute('aria-label','Compare '+record.title);label.append(check);check.addEventListener('change',()=>{if(check.checked&&selected.size===3){check.checked=false;announce('Choose up to three records to compare.');return;}if(check.checked)selected.add(record.id);else selected.delete(record.id);updateReadingCompare();});
   const copy=make('div'),ref=make('p','ax-label',record.accession),title=make('h3'),link=make('a',null,record.short_title||record.title);link.href=href('items/'+record.id+'.html');link.dataset.axHandoff='';title.append(link);copy.append(ref,title,make('p',null,record.author+' · '+record.date));
   const remove=make('button',null,'Remove');remove.type='button';remove.setAttribute('aria-label','Remove '+record.title);remove.addEventListener('click',()=>{saved=saved.filter(id=>id!==record.id);selected.delete(record.id);persist();renderReading();announce('Removed from your reading list.');});article.append(label,copy,remove);host.append(article);
  });
  $('[data-ax-export]').disabled=!known.length;$('[data-ax-clear]').disabled=!saved.length;updateReadingCompare();
  if(!storageOK)announce('Browser storage is unavailable. Your reading list lasts for this visit.');
 }
 root.addEventListener('click',event=>{
  const save=event.target.closest('[data-ax-save]');if(save&&root.contains(save)){const id=save.dataset.axSave,active=saved.includes(id);saved=core.toggleSaved(saved,id);if(active)selected.delete(id);persist();announce(active?'Removed from your reading list.':storageOK?'Added to your reading list.':'Added for this visit; browser storage is unavailable.');return;}
  const link=event.target.closest('a');if(!link||!root.contains(link)||event.button>0||event.metaKey||event.ctrlKey||event.shiftKey||event.altKey)return;
  if(link.dataset.axView){event.preventDefault();show(link.dataset.axView,{push:true,focus:true});}
  else if(link.dataset.axCollection){event.preventDefault();state.collection=link.dataset.axCollection;show('catalogue',{push:true,focus:true});}
  else if(link.hasAttribute('data-ax-handoff'))link.href=handoffURL(link.href,saved,root.dataset.origin,win.location.href);
 });
 // Set handoff URLs also for modified clicks and keyboard/context-menu opening.
 root.addEventListener('pointerdown',event=>{const a=event.target.closest('a[data-ax-handoff]');if(a&&root.contains(a))a.href=handoffURL(a.href,saved,root.dataset.origin,win.location.href);});
 $('[data-ax-entry]').addEventListener('submit',event=>{event.preventDefault();const q=event.target.elements.namedItem('q').value;const input=$('#ax-discovery-query');input.value=q;state.dq=q;show('discover',{push:true,focus:true});input.dispatchEvent(new win.Event('input',{bubbles:true}));});
 filter.addEventListener('input',()=>{for(const key of ['q','collection','year','type','sort'])state[key]=filter.elements.namedItem(key).value;filters();setHash();});
 $('[data-discovery-form]').addEventListener('input',()=>{const form=$('[data-discovery-form]');state.dq=form.elements.namedItem('q').value;state.dk=form.elements.namedItem('kind').value;state.fulltext=form.elements.namedItem('fulltext').checked;setHash();});
 filter.addEventListener('submit',event=>event.preventDefault());filter.addEventListener('reset',event=>{event.preventDefault();state={...state,q:'',collection:'',year:'',type:'',sort:'newest'};filters();setHash();});
 $$('[data-ax-layout]').forEach(button=>button.addEventListener('click',()=>{state.layout=button.dataset.axLayout;filters();setHash();}));
 $('[data-ax-clear]').addEventListener('click',()=>{saved=[];selected.clear();$('[data-ax-comparison]').replaceChildren();persist();renderReading();announce('Reading list cleared.');});
 $('[data-ax-export]').addEventListener('click',()=>{const blob=new win.Blob([core.csv(saved.map(id=>byId.get(id)).filter(Boolean))],{type:'text/csv;charset=utf-8;'}),url=win.URL.createObjectURL(blob),a=make('a');a.href=url;a.download='museum-of-one-reading-list.csv';a.click();win.setTimeout(()=>win.URL.revokeObjectURL(url),1000);});
 $('[data-ax-compare]').addEventListener('click',()=>{if(selected.size<2||selected.size>3)return;const chosen=[...selected].map(id=>byId.get(id)),table=make('table'),caption=make('caption',null,'Selected catalogue records; dates retain their source precision.'),head=make('thead'),tr=make('tr');tr.append(make('th',null,'Description'));chosen.forEach(r=>tr.append(make('th',null,r.short_title||r.title)));head.append(tr);const body=make('tbody');core.comparisonRows(chosen).forEach(row=>{const tr=make('tr'),th=make('th',null,row.label);th.scope='row';tr.append(th);row.values.forEach(value=>tr.append(make('td',null,value)));body.append(tr);});table.append(caption,head,body);const scroll=make('div','ax-table-scroll');scroll.append(table);$('[data-ax-comparison]').replaceChildren(scroll);});
 function expand(next){expanded=next;const button=$('[data-ax-expand]');root.classList.toggle('ax-expanded',next);button.setAttribute('aria-pressed',String(next));button.textContent=next?'Return to page':'Expand explorer';if(next){previousOverflow=doc.body.style.overflow;doc.body.style.overflow='hidden';root.setAttribute('role','dialog');root.setAttribute('aria-modal','true');for(let branch=root;branch.parentElement&&branch!==doc.body;branch=branch.parentElement){for(const sibling of branch.parentElement.children)if(sibling!==branch&&!sibling.inert&&!['SCRIPT','STYLE','LINK'].includes(sibling.tagName)){sibling.inert=true;inertElements.push(sibling);}}button.focus();}else{doc.body.style.overflow=previousOverflow;root.removeAttribute('role');root.removeAttribute('aria-modal');inertElements.forEach(n=>n.inert=false);inertElements=[];button.focus();}}
 $('[data-ax-expand]').hidden=false;$('[data-ax-expand]').addEventListener('click',()=>expand(!expanded));
 root.addEventListener('keydown',event=>{if(!expanded)return;if(event.key==='Escape'){event.preventDefault();expand(false);}else if(event.key==='Tab'){const all=$$('a[href],button:not([disabled]),input:not([disabled]),select:not([disabled]),summary').filter(n=>n.getClientRects().length),first=all[0],last=all.at(-1);if(event.shiftKey&&doc.activeElement===first){event.preventDefault();last.focus();}else if(!event.shiftKey&&doc.activeElement===last){event.preventDefault();first.focus();}}});
 win.addEventListener('popstate',()=>{state=readState(win.location.hash);show(state.view);});
 const receive=event=>{try{saved=core.parseSaved(event?.type==='moo-reading-list-change'?JSON.stringify(event.detail):win.localStorage.getItem(STORAGE));}catch{return;}sync();if(state.view==='reading')renderReading();};
 win.addEventListener('storage',event=>{if(event.key===STORAGE)receive(event);});win.addEventListener('moo-reading-list-change',receive);
 doc.querySelectorAll('a[href="#archive-search"]').forEach(link=>link.addEventListener('click',event=>{event.preventDefault();show('discover',{push:true,focus:true});}));
 sync();show(state.view);return{show,root};
}
return{STORAGE,shelfIds,handoffURL,readState,stateHash,mount};
});
