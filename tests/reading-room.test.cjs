const test=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
const core=require('../dist/assets/archive-core.js');
const records=JSON.parse(fs.readFileSync(path.join(__dirname,'../dist/metadata/discovery.json'),'utf8'));
const script=fs.readFileSync(path.join(__dirname,'../dist/assets/app.js'),'utf8');
const tick=()=>new Promise(resolve=>setImmediate(resolve));
function fixture({blocked=false,fetchFails=false}={}){
 const sets=new Map(),byId=new Map(),storage=new Map();
 class Element{
  constructor(id,dataset={}){this.id=id;this.dataset=dataset;this.listeners={};this.attrs={};this.open=false;this.textContent='';this.checked=false;this.disabled=false;this.classList={add(){},remove(){},toggle(){}};this._html='';}
  addEventListener(name,fn){(this.listeners[name]??=[]).push(fn)}
  async fire(name,event={}){for(const fn of this.listeners[name]||[])await fn({target:this,...event})}
  setAttribute(k,v){this.attrs[k]=v}
  closest(selector){return selector==='dialog'?this.dialog:null}
  showModal(){this.open=true}
  close(){this.open=false;this.fire('close')}
  set innerHTML(value){this._html=value;if(this.id==='reading-records'){
   const inputs=[...value.matchAll(/data-select-compare="([^"]+)"/g)].map(m=>new Element('',{selectCompare:m[1]}));
   const removes=[...value.matchAll(/data-remove-saved="([^"]+)"/g)].map(m=>new Element('',{removeSaved:m[1]}));
   sets.set('[data-select-compare]',inputs);sets.set('[data-remove-saved]',removes);
  }}
  get innerHTML(){return this._html}
 }
 const ids=['reading-dialog','comparison-dialog','cover-dialog','archive-toast','reading-records','reading-message','compare-records','export-reading','clear-reading','comparison-content','cover-image','cover-caption','evidence-filter','hero-cover','hero-record-link','hero-selected-caption'];
 ids.forEach(id=>byId.set(id,new Element(id)));
 const button=new Element('',{save:'19864099'}),duplicate=new Element('',{save:'19864099'}),opener=new Element(),counter=new Element(),cover=new Element('',{coverSrc:'../assets/foundational-essays.jpg',coverCaption:'Published cover'});
 sets.set('[data-save]',[button,duplicate]);sets.set('[data-reading-count]',[counter]);sets.set('[data-open-reading]',[opener]);sets.set('[data-cover-src]',[cover]);sets.set('dialog',['reading-dialog','comparison-dialog','cover-dialog'].map(id=>byId.get(id)));
 const doc={body:{dataset:{root:'../'}},querySelector:s=>s.startsWith('#')?byId.get(s.slice(1))||null:null,querySelectorAll:s=>sets.get(s)||[],addEventListener(){}};
 const localStorage={getItem(k){if(blocked)throw Error('blocked');return storage.get(k)||null},setItem(k,v){if(blocked)throw Error('blocked');storage.set(k,v)}};
 const context={document:doc,ArchiveCore:core,localStorage,window:{addEventListener(){}},location:{href:'https://museum.example/items/19864099.html',search:'',pathname:'/items/19864099.html'},URL,URLSearchParams,fetch:async()=>({ok:!fetchFails,json:async()=>records}),setTimeout:()=>1,clearTimeout(){},Blob};
 vm.runInNewContext(script,context);
 return {byId,sets,button,duplicate,opener,counter,cover,storage};
}
test('save buttons synchronize, persist, and populate the reading list',async()=>{
 const f=fixture();await f.button.fire('click');assert.equal(f.counter.textContent,1);assert.equal(f.duplicate.attrs['aria-pressed'],'true');assert.ok([...f.storage.values()][0].includes('19864099'));
 await f.opener.fire('click');await tick();assert.ok(f.byId.get('reading-dialog').open);assert.ok(f.byId.get('reading-records').innerHTML.includes('Volume I'));
 await f.button.fire('click');assert.equal(f.counter.textContent,0);assert.equal(f.duplicate.attrs['aria-pressed'],'false');
});
test('storage failure keeps the current reading session usable',async()=>{
 const f=fixture({blocked:true});await f.button.fire('click');await f.opener.fire('click');await tick();assert.equal(f.counter.textContent,1);assert.match(f.byId.get('reading-message').textContent,/storage is unavailable/);assert.ok(f.byId.get('reading-records').innerHTML.includes('Volume I'));
});
test('cover view resolves the relative cover path safely',async()=>{
 const f=fixture();await f.cover.fire('click');assert.equal(f.byId.get('cover-image').src,'https://museum.example/assets/foundational-essays.jpg');assert.equal(f.byId.get('cover-caption').textContent,'Published cover');assert.equal(f.byId.get('cover-dialog').open,true);
});
test('comparison opens only with two selected saved records',async()=>{
 const f=fixture();await f.button.fire('click');f.button.dataset.save='19864115';await f.button.fire('click');await f.opener.fire('click');await tick();
 const inputs=f.sets.get('[data-select-compare]');assert.equal(inputs.length,2);inputs[0].checked=true;await inputs[0].fire('change');assert.equal(f.byId.get('compare-records').disabled,true);inputs[1].checked=true;await inputs[1].fire('change');assert.equal(f.byId.get('compare-records').disabled,false);
 await f.byId.get('compare-records').fire('click');await tick();assert.equal(f.byId.get('comparison-dialog').open,true);assert.equal(f.byId.get('reading-dialog').open,false);assert.match(f.byId.get('comparison-content').innerHTML,/month precision/);assert.match(f.byId.get('comparison-content').innerHTML,/Version-family DOI/);
});
