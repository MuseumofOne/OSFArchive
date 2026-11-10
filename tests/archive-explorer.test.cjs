const test=require('node:test'),assert=require('node:assert/strict');
const explorer=require('../dist/assets/archive-explorer.js');
const origin='https://archive.museumofone.art';
test('reading handoff carries only bounded numeric archive IDs and retains PDF page destinations',()=>{
 assert.deepEqual(explorer.shelfIds('19864099,23395654,19864099'),['19864099','23395654']);
 for(const value of ['<script>','123,evil','1,'.repeat(3000),null,'123,,234'])assert.deepEqual(explorer.shelfIds(value),[]);
 const u=new URL(explorer.handoffURL(origin+'/read/23395654.html#page=113',['19864099','23395654'],origin,'https://www.museumofone.art/digital-archive-library/'));
 assert.equal(u.hash,'#page=113');assert.equal(u.searchParams.get('moo_shelf'),'19864099,23395654');
 assert.equal(explorer.handoffURL('https://zenodo.org/records/123', ['19864099'],origin,origin), 'https://zenodo.org/records/123');
});
test('explorer state round-trips combined filters without taking over the host page query',()=>{
 const state={view:'catalogue',q:'Hassan Sharif',collection:'Books & volumes',year:'2026',type:'Book',sort:'title',layout:'list',dq:'lived experience',dk:'publication',fulltext:true};
 assert.deepEqual(explorer.readState(explorer.stateHash(state)),state);
 assert.equal(explorer.readState('#ax:view=javascript:alert(1)').view,'overview');
 assert.equal(explorer.readState('#page=182').view,'overview');
 assert.equal(explorer.readState('#public-catalogue').view,'catalogue');
});
test('catalogue defaults to the latest publication and preserves explicit reference order',()=>{
 assert.equal(explorer.readState('#ax:view=catalogue&collection=Essays').sort,'newest');
 assert.equal(explorer.readState('#public-catalogue').sort,'newest');
 assert.equal(explorer.readState(explorer.stateHash({view:'catalogue',sort:'reference'})).sort,'reference');
});
