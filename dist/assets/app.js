/* Browser-local research tools; all work descriptions come from the static catalogue. */
'use strict';
const $=s=>document.querySelector(s), $$=s=>[...document.querySelectorAll(s)];
const core=globalThis.ArchiveCore;
const base=document.body.dataset.root||'';
const escapeHTML=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const safeURL=value=>{try{const url=new URL(value,location.href);return /^https?:$/.test(url.protocol)?url.href:'#';}catch{return '#';}};
const recordURL=r=>base+'items/'+encodeURIComponent(r.id)+'.html';
const storageKey='museum-of-one-reading-list-v1';
let saved=[],storageAvailable=true,selected=new Set(),discoveryPromise;
try{saved=core.parseSaved(localStorage.getItem(storageKey));}catch{storageAvailable=false;}
let toastTimer;
function toast(message){const el=$('#archive-toast');if(!el)return;el.textContent=message;el.classList.add('visible');clearTimeout(toastTimer);toastTimer=setTimeout(()=>el.classList.remove('visible'),3000);}
function persist(){try{localStorage.setItem(storageKey,JSON.stringify(saved));}catch{storageAvailable=false;}syncSaveButtons();}
function syncSaveButtons(){
 $$('[data-reading-count]').forEach(el=>el.textContent=saved.length);
 $$('[data-save]').forEach(button=>{const active=saved.includes(button.dataset.save);button.setAttribute('aria-pressed',String(active));button.classList.toggle('is-saved',active);button.innerHTML=active?'✓ Saved':'＋ Save'+(button.closest('.item-head')?' to reading list':'');});
}
function loadDiscovery(){
 if(!discoveryPromise)discoveryPromise=fetch(base+'metadata/discovery.json').then(r=>{if(!r.ok)throw new Error('Catalogue unavailable');return r.json();}).then(records=>{if(!Array.isArray(records))throw new Error('Invalid catalogue');return records;}).catch(error=>{discoveryPromise=null;throw error;});
 return discoveryPromise;
}
$$('[data-save]').forEach(button=>button.addEventListener('click',()=>{const active=saved.includes(button.dataset.save);saved=core.toggleSaved(saved,button.dataset.save);if(active)selected.delete(button.dataset.save);persist();toast(active?'Removed from your reading list':storageAvailable?'Added to your reading list':'Added for this visit; browser storage is unavailable');}));
syncSaveButtons();
window.addEventListener('storage',event=>{if(event.key===storageKey){saved=core.parseSaved(event.newValue);selected=new Set([...selected].filter(id=>saved.includes(id)));syncSaveButtons();if($('#reading-dialog')?.open)renderReading();}});
const search=$('#catalogue-search');
if(search){
 const cards=$$('[data-record]');
 const fields={q:search,collection:$('#group-filter'),year:$('#year-filter'),subject:$('#subject-filter'),type:$('#type-filter'),programme:$('#programme-filter')};
 const params=new URLSearchParams(location.search),sort=$('#sort'),grid=$('#catalogue-grid');
 Object.entries(fields).forEach(([key,field])=>{const value=params.get(key)||'';field.value=value;if(field.value!==value)field.value='';});
 const data=card=>({...card.dataset,subjects:JSON.parse(card.dataset.subjects||'[]'),programmes:JSON.parse(card.dataset.programmes||'[]')});
 let view=params.get('view')==='list'?'list':'grid';
 function setView(next){view=next;grid.dataset.view=view;$$('[data-view]').filter(el=>el.tagName==='BUTTON').forEach(button=>button.setAttribute('aria-pressed',String(button.dataset.view===view)));}
 function updateURL(){const next=new URLSearchParams();Object.entries(fields).forEach(([key,el])=>{if(el.value)next.set(key,el.value);});if(view==='list')next.set('view','list');if(sort.value!=='newest')next.set('sort',sort.value);history.replaceState(null,'',location.pathname+(next.size?'?'+next:'')+location.hash);}
 function update(){
  const filters=Object.fromEntries(Object.entries(fields).map(([key,el])=>[key,el.value]));let count=0;
  cards.forEach(card=>{const show=core.matches(data(card),filters);card.hidden=!show;if(show)count++;});
  $('#result-count').textContent=count+' '+(count===1?'record':'records');$('#no-results').hidden=count!==0;
  const chips=$('#active-filters');chips.replaceChildren();
  Object.entries(fields).forEach(([key,el])=>{if(!el.value)return;const chip=document.createElement('button');chip.type='button';chip.className='filter-chip';const label=el.tagName==='SELECT'?el.selectedOptions[0].textContent:el.value;chip.textContent=(key==='q'?'Search: ':'')+label+' ×';chip.setAttribute('aria-label','Remove filter '+label);chip.addEventListener('click',()=>{el.value='';update();el.focus();});chips.append(chip);});
  updateURL();
 }
 function sortCards(){const sorted=[...cards].sort((a,b)=>sort.value==='title'?a.dataset.title.localeCompare(b.dataset.title):sort.value==='oldest'?a.dataset.date.localeCompare(b.dataset.date):b.dataset.date.localeCompare(a.dataset.date));sorted.forEach(card=>grid.append(card));}
 if(['newest','oldest','title'].includes(params.get('sort')))sort.value=params.get('sort');
 Object.values(fields).forEach(field=>field.addEventListener('input',update));
 sort.addEventListener('change',()=>{sortCards();updateURL();});
 $$('button[data-view]').forEach(button=>button.addEventListener('click',()=>{setView(button.dataset.view);updateURL();}));
 $('#reset-filters').addEventListener('click',()=>{Object.values(fields).forEach(field=>field.value='');update();search.focus();});
 setView(view);sortCards();update();
}
const reading=$('#reading-dialog'),compare=$('#comparison-dialog');
function updateCompare(){const button=$('#compare-records');button.disabled=selected.size<2||selected.size>3;button.textContent=selected.size?'Compare '+selected.size+' selected records':'Compare selected records';}
async function renderReading(){
 $('#reading-records').innerHTML='<p class="reading-empty">Opening the catalogue…</p>';
 try{
  const records=await loadDiscovery();const byId=new Map(records.map(r=>[r.id,r]));const known=saved.map(id=>byId.get(id)).filter(Boolean);
  selected=new Set([...selected].filter(id=>saved.includes(id)&&byId.has(id)));
  $('#reading-message').textContent=!storageAvailable?'Browser storage is unavailable. This list lasts for this visit.':saved.length!==known.length?'Some saved records are not present in this catalogue edition.':'';
  $('#reading-records').innerHTML=known.length?known.map(r=>'<article class="reading-entry"><label class="compare-check"><input type="checkbox" data-select-compare="'+escapeHTML(r.id)+'" '+(selected.has(r.id)?'checked':'')+'><span class="sr-only">Compare '+escapeHTML(r.title)+'</span></label><div><span class="catalogue-id">'+escapeHTML(r.accession)+' / '+escapeHTML(r.type)+'</span><h3><a href="'+recordURL(r)+'">'+escapeHTML(r.short_title||r.title)+'</a></h3><p>'+escapeHTML(r.author)+' · '+escapeHTML(r.date)+'</p></div><button type="button" class="text-button" data-remove-saved="'+escapeHTML(r.id)+'" aria-label="Remove '+escapeHTML(r.title)+'">Remove</button></article>').join(''):'<div class="reading-empty"><h3>A shelf of your own.</h3><p>Use “Save” on any catalogue record to keep it here.</p><a class="text-link" href="'+base+'catalogue.html">Explore the catalogue ↗</a></div>';
  $$('[data-select-compare]').forEach(input=>input.addEventListener('change',()=>{if(input.checked&&selected.size>=3){input.checked=false;toast('Choose up to three records to compare');return;}if(input.checked)selected.add(input.dataset.selectCompare);else selected.delete(input.dataset.selectCompare);updateCompare();}));
  $$('[data-remove-saved]').forEach(button=>button.addEventListener('click',()=>{saved=saved.filter(id=>id!==button.dataset.removeSaved);selected.delete(button.dataset.removeSaved);persist();renderReading();}));
  $('#export-reading').disabled=!known.length;$('#clear-reading').disabled=!saved.length;updateCompare();
 }catch{$('#reading-records').innerHTML='<p>The catalogue could not be loaded. Your saved list has been kept.</p><button type="button" class="button outline" id="retry-reading">Try again</button>';$('#retry-reading').addEventListener('click',renderReading);$('#compare-records').disabled=true;$('#export-reading').disabled=true;}
}
$$('[data-open-reading]').forEach(button=>button.addEventListener('click',()=>{reading.showModal();renderReading();}));
$$('[data-close-dialog]').forEach(button=>button.addEventListener('click',()=>button.closest('dialog').close()));
$$('dialog').forEach(dialog=>dialog.addEventListener('click',event=>{if(event.target===dialog){const box=dialog.getBoundingClientRect();if(event.clientX<box.left||event.clientX>box.right||event.clientY<box.top||event.clientY>box.bottom)dialog.close();}}));
$('#clear-reading')?.addEventListener('click',()=>{saved=[];selected.clear();persist();renderReading();});
$('#export-reading')?.addEventListener('click',async()=>{try{const records=await loadDiscovery();const blob=new Blob([core.csv(saved.map(id=>records.find(r=>r.id===id)).filter(Boolean))],{type:'text/csv;charset=utf-8;'});const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download='museum-of-one-reading-list.csv';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}catch{toast('The reading list could not be exported. Please try again.');}});
$('#compare-records')?.addEventListener('click',async()=>{if(selected.size<2||selected.size>3)return;try{const records=await loadDiscovery();const chosen=[...selected].map(id=>records.find(r=>r.id===id)).filter(Boolean);if(chosen.length<2)return;$('#comparison-content').innerHTML='<p class="dialog-intro">Dates retain their source precision. A repository version, first edition, and web article may have different dates.</p><div class="table-scroll"><table class="comparison-table"><caption class="sr-only">Comparison of selected catalogue records</caption><thead><tr><th scope="col">Description</th>'+chosen.map(r=>'<th scope="col"><span class="catalogue-id">'+escapeHTML(r.accession)+'</span><a href="'+recordURL(r)+'">'+escapeHTML(r.short_title||r.title)+'</a></th>').join('')+'</tr></thead><tbody>'+core.comparisonRows(chosen).map(row=>'<tr><th scope="row">'+escapeHTML(row.label)+'</th>'+row.values.map(v=>'<td>'+escapeHTML(v)+'</td>').join('')+'</tr>').join('')+'</tbody></table></div>';reading.close();compare.showModal();}catch{toast('The comparison could not be loaded. Your list has been kept.');}});
compare?.addEventListener('close',()=>{reading.showModal();renderReading();});
$$('[data-cover-src]').forEach(button=>button.addEventListener('click',()=>{const img=$('#cover-image');img.src=safeURL(button.dataset.coverSrc);img.alt=button.dataset.coverCaption||'Publication cover';$('#cover-caption').textContent=button.dataset.coverCaption||'';$('#cover-dialog').showModal();}));
let featureRequest=0;
$$('[data-featured]').forEach(button=>button.addEventListener('click',async()=>{const request=++featureRequest;try{const records=await loadDiscovery();if(request!==featureRequest)return;const r=records.find(x=>x.id===button.dataset.featured);if(!r?.cover)return;const img=$('#hero-cover');img.src=safeURL(base+r.cover);img.alt=r.cover_alt||r.title;$('#hero-record-link').href=recordURL(r);const caption=$('#hero-selected-caption');caption.href=recordURL(r);caption.textContent=(r.short_title||r.title)+' ↗';$('.hero-shelf-number').textContent=button.textContent;$$('[data-featured]').forEach(b=>b.setAttribute('aria-pressed',String(b===button)));}catch{toast('The featured record could not be loaded. Please try again.');}}));
$('#evidence-filter')?.addEventListener('input',event=>{$$('[data-evidence-status]').forEach(row=>row.hidden=Boolean(event.target.value&&row.dataset.evidenceStatus!==event.target.value));});
$$('[data-copy]').forEach(button=>button.addEventListener('click',async()=>{const text=document.getElementById(button.dataset.copy).textContent;try{await navigator.clipboard.writeText(text);button.textContent='Citation copied';}catch{const range=document.createRange();range.selectNodeContents(document.getElementById(button.dataset.copy));getSelection().removeAllRanges();getSelection().addRange(range);button.textContent='Citation selected — copy to clipboard';}setTimeout(()=>button.textContent='Copy citation',3000);}));
document.addEventListener('keydown',event=>{if(event.key!=='/'||event.ctrlKey||event.metaKey||event.altKey||event.target.closest('input,textarea,select,[contenteditable="true"]')||$$('dialog').some(d=>d.open))return;event.preventDefault();if(search)search.focus();else location.href=base+'catalogue.html#catalogue-search';});
