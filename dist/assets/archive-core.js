(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else root.ArchiveCore=api;})(typeof globalThis!=='undefined'?globalThis:this,function(){
'use strict';
const normalize=value=>String(value||'').normalize('NFKD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
function matches(data,filters){
 const terms=normalize(filters.q).trim().split(/\s+/).filter(Boolean);
 return terms.every(t=>normalize(data.search).includes(t)) && (!filters.collection||data.group===filters.collection) && (!filters.year||data.year===filters.year) && (!filters.subject||(data.subjects||[]).includes(filters.subject)) && (!filters.type||data.type===filters.type) && (!filters.programme||(data.programmes||[]).includes(filters.programme));
}
function parseSaved(raw){try{const values=JSON.parse(raw);return Array.isArray(values)?[...new Set(values.filter(v=>typeof v==='string'&&/^[a-zA-Z0-9_-]{1,80}$/.test(v)))].slice(0,200):[];}catch{return [];}}
function toggleSaved(ids,id){if(!/^[a-zA-Z0-9_-]{1,80}$/.test(id))return ids;return ids.includes(id)?ids.filter(x=>x!==id):[...ids,id].slice(-200);}
function csv(records){const fields=['Item number','Title','Creator','Source publication date','Resource type','Medium','Edition DOI','Museum of One record'];const quote=v=>'"'+String(v??'').replace(/"/g,'""')+'"';const safe=v=>{const s=String(v??'');return /^[=+\-@\t\r]/.test(s)?"'"+s:s;};return '\ufeff'+[fields,...records.map(r=>[r.accession,r.title,r.author,r.date,r.type,r.medium,r.doi,r.institutional_url])].map(row=>row.map(v=>quote(safe(v))).join(',')).join('\r\n');}
function comparisonRows(records){const list=x=>Array.isArray(x)?x.join(' · '):x;return [
 ['Item number',r=>r.accession],['Creator',r=>r.author],['Source publication date',r=>r.date+(r.date_precision?' ('+r.date_precision+' precision)':'')],['Resource type',r=>r.type],['Medium / format',r=>[r.medium,list(r.digital_formats)].filter(Boolean).join(' · ')],['Extent',r=>r.extent],['Edition statement',r=>r.edition_statement||r.first_edition],['Edition DOI',r=>r.doi],['Version-family DOI',r=>r.conceptdoi],['ISBN',r=>r.isbn?r.isbn+' (source identifier; check the item record for format and edition applicability)':null],['Language',r=>r.language],['Licence',r=>r.license?.label],['Editorial subjects',r=>list(r.subjects)],['Programme context',r=>(r.research_programmes||[]).map(p=>p.title+' — '+p.status).join('; ')]
 ].map(([label,get])=>({label,values:records.map(r=>get(r)||'Not supplied / not applicable')}));}
return {normalize,matches,parseSaved,toggleSaved,csv,comparisonRows};
});
