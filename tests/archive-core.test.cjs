const {test}=require('node:test');const assert=require('node:assert/strict');const fs=require('node:fs');const path=require('node:path');
const core=require('../dist/assets/archive-core.js');
const records=JSON.parse(fs.readFileSync(path.join(__dirname,'../dist/metadata/discovery.json'),'utf8'));
const programmeId=p=>p.url.split('/').filter(Boolean).at(-1);
const searchData=r=>({search:[r.title,r.accession,r.author,r.doi,r.isbn,r.summary,...r.subjects].filter(Boolean).join(' '),group:r.collection,year:r.date.slice(0,4),subjects:r.subjects,type:r.type,programmes:r.research_programmes.map(programmeId)});
test('catalogue combines identifier, programme, medium/type and date filters',()=>{
 assert.equal(records.filter(r=>core.matches(searchData(r),{q:'MOO-CAT-001'})).length,1);
 assert.equal(records.filter(r=>core.matches(searchData(r),{q:'10.5281/zenodo.23428974'})).length,1);
 assert.equal(records.filter(r=>core.matches(searchData(r),{type:'Book',programme:'research-witness-material-memory'})).length,3);
 assert.ok(records.filter(r=>core.matches(searchData(r),{q:'post-interpretive',year:'2025'})).every(r=>r.date.startsWith('2025')));
 assert.equal(records.filter(r=>core.matches(searchData(r),{q:'nonexistent-record-term'})).length,0);
});
test('query normalization supports accents and combined terms',()=>{assert.equal(core.matches({search:'Éthique of witnessing — Dorian Vale',subjects:[],programmes:[]},{q:'ethique VALE'}),true);assert.equal(core.matches({search:'ethique',subjects:[],programmes:[]},{q:'ethique missing'}),false);});
test('reading list tolerates malformed or unexpected browser storage',()=>{for(const x of ['null','{}','invalid','"one"'])assert.deepEqual(core.parseSaved(x),[]);assert.deepEqual(core.parseSaved('["19864099","19864099",1,"../bad","23428974"]'),['19864099','23428974']);const ids=core.toggleSaved([],'19864099');assert.deepEqual(core.toggleSaved(ids,'19864099'),[]);assert.deepEqual(core.toggleSaved(ids,'bad/id'),ids);});
test('CSV export quotes titles and is safe to open as a spreadsheet',()=>{const csv=core.csv([{accession:'MOO-CAT-X',title:'An "archive", revisited\nsecond line',author:'=SUM(A1:A2)',date:'2025',type:'Book'}]);assert.ok(csv.includes('"An ""archive"", revisited\nsecond line"'));assert.ok(csv.includes('"\'=SUM(A1:A2)"'));assert.ok(csv.startsWith('\ufeff'));});
test('record comparison preserves date precision and corrected ISBN scope',()=>{const manual=records.find(r=>r.id==='20100136');assert.equal(manual.isbn,null);const rows=core.comparisonRows([records[0],manual]);assert.equal(rows.find(r=>r.label==='ISBN').values[1],'Not supplied / not applicable');assert.ok(rows.find(r=>r.label==='Source publication date').values[0].includes('month precision'));assert.equal(rows.find(r=>r.label==='Item number').values.length,2);});
