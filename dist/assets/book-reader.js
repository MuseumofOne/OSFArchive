import './reader-core.js';

const root=document.getElementById('book-reader');
if(root) startReader(root);

async function startReader(root){
 const core=globalThis.ReaderCore;
 const get=id=>document.getElementById('reader-'+id);
 const stage=get('stage'),pages=get('pages'),status=get('status'),loading=get('loading');
 const shell=root.closest('.reader-shell')||root;
 const controls={prev:get('prev'),next:get('next'),zoomOut:get('zoom-out'),zoomIn:get('zoom-in'),fit:get('fit'),fullscreen:get('fullscreen'),thumbsToggle:get('thumbs-toggle'),page:get('page'),mode:get('mode'),progress:get('progress')};
 const thumbnails=get('thumbnails'),thumbList=get('thumb-list');
 const wide=window.matchMedia('(min-width: 1000px)');
 let pdf,loadTask,manifest,currentPage=1,zoom=1,requestId=0,renderTasks=new Set(),thumbsBuilt=false,resizeTimer,observer,thumbQueue=[],thumbBusy=0,destroyed=false;
 let mode=controls.mode?.value||'auto';
 const effectiveMode=()=>mode==='auto'?(wide.matches?'spread':'single'):mode;
 const total=()=>pdf?.numPages||1;
 const abortRender=()=>{for(const task of renderTasks){try{task.cancel();}catch{}}renderTasks.clear();};
 const message=text=>{if(status)status.textContent=text;};
 function setBusy(value){stage?.setAttribute('aria-busy',String(value));if(loading)loading.hidden=!value;}
 function syncControls(){
  if(!pdf)return;
  const visible=core.pagesFor(currentPage,total(),effectiveMode());
  if(controls.prev)controls.prev.disabled=visible[0]===1;
  if(controls.next)controls.next.disabled=visible.at(-1)>=total();
  if(controls.zoomOut)controls.zoomOut.disabled=zoom<=1;
  if(controls.zoomIn)controls.zoomIn.disabled=zoom>=3;
  if(controls.page){controls.page.value=currentPage;controls.page.max=total();controls.page.min=1;}
  if(controls.progress){controls.progress.value=currentPage;controls.progress.max=total();controls.progress.min=1;controls.progress.setAttribute('aria-valuetext','Page '+currentPage+' of '+total());}
  get('total').textContent=total();
  if(controls.fit)controls.fit.textContent=zoom===1?'Fit page':'Fit page · '+Math.round(zoom*100)+'%';
  for(const button of thumbList?.querySelectorAll('[data-page]')||[]){const active=visible.includes(Number(button.dataset.page));button.setAttribute('aria-current',active?'page':'false');}
 }
 function updateHash(){const url=new URL(location.href);url.hash='page='+currentPage;history.replaceState(null,'',url.pathname+url.search+url.hash);}
 async function showPage(value,{hash=true}={}){
  if(!pdf||destroyed)return;
  currentPage=core.clampPage(value,total());
  const token=++requestId;abortRender();syncControls();if(hash)updateHash();setBusy(true);
  const visible=core.pagesFor(currentPage,total(),effectiveMode());
  message('Opening '+(visible.length>1?'pages '+visible.join('–'):'page '+visible[0])+'…');
  try{
   const documents=await Promise.all(visible.map(number=>pdf.getPage(number)));
   if(token!==requestId||destroyed)return;
   const dimensions=documents.map(page=>page.getViewport({scale:1}));
   const rect=stage.getBoundingClientRect();
   const fit=core.fitScale(dimensions,Math.max(100,rect.width-48),Math.max(140,rect.height-48),8);
   const scale=fit*zoom;
   const fragment=document.createDocumentFragment();
   const work=[];
   documents.forEach((page,index)=>{
    const pageNumber=visible[index],viewport=page.getViewport({scale});
    const figure=document.createElement('figure');figure.className='reader-folio';figure.dataset.page=pageNumber;figure.style.width=viewport.width+'px';
    const canvas=document.createElement('canvas');canvas.className='reader-canvas';canvas.setAttribute('role','img');canvas.setAttribute('aria-label','Page '+pageNumber+' of '+total());
    const ratio=Math.min(window.devicePixelRatio||1,1.75);canvas.width=Math.ceil(viewport.width*ratio);canvas.height=Math.ceil(viewport.height*ratio);canvas.style.width=viewport.width+'px';canvas.style.height=viewport.height+'px';
    const caption=document.createElement('figcaption');caption.textContent='PAGE '+pageNumber;figure.append(canvas,caption);fragment.append(figure);
    const task=page.render({canvasContext:canvas.getContext('2d',{alpha:false}),viewport,transform:ratio!==1?[ratio,0,0,ratio,0,0]:undefined,background:'rgb(255,255,255)'});renderTasks.add(task);
    work.push(task.promise.finally(()=>renderTasks.delete(task)));
    // Make document text available without pretending the raster is selectable text.
    page.getTextContent().then(content=>{
     if(token!==requestId||destroyed)return;
     const text=content.items.map(item=>item.str+(item.hasEOL?'\n':' ')).join('').trim();
     if(!text)return;
     const details=document.createElement('details');details.className='reader-page-text';const summary=document.createElement('summary');summary.textContent='Page '+pageNumber+' text';const paragraph=document.createElement('p');paragraph.textContent=text;details.append(summary,paragraph);figure.append(details);
    }).catch(()=>{});
   });
   pages.replaceChildren(fragment);pages.dataset.layout=visible.length>1?'spread':'single';
   await Promise.all(work);
   if(token!==requestId||destroyed)return;
   setBusy(false);message((visible.length>1?'Pages '+visible.join('–'):'Page '+visible[0])+' of '+total()+' · '+(effectiveMode()==='spread'?'Facing pages':'Single page'));
   stage.scrollLeft=0;stage.scrollTop=0;
  }catch(error){
   if(token!==requestId||destroyed||error?.name==='RenderingCancelledException')return;
   setBusy(false);message('This page could not be rendered. Try another page or open the original PDF below.');
  }
 }
 function navigate(direction){showPage(direction>0?core.nextPage(currentPage,total(),effectiveMode()):core.previousPage(currentPage,total(),effectiveMode()));}
 function goToInput(){const value=Number(controls.page.value);showPage(Number.isFinite(value)?value:currentPage);}
 function scheduleThumb(){
  if(!pdf||destroyed||thumbnails?.hidden)return;
  while(thumbBusy<2&&thumbQueue.length){const entry=thumbQueue.shift();if(entry.rendered||entry.rendering)continue;entry.rendering=true;thumbBusy++;
   pdf.getPage(entry.number).then(page=>{
    if(destroyed)return;
    const base=page.getViewport({scale:1}),viewport=page.getViewport({scale:105/base.width});const canvas=document.createElement('canvas');canvas.width=Math.ceil(viewport.width);canvas.height=Math.ceil(viewport.height);canvas.setAttribute('aria-hidden','true');
    return page.render({canvasContext:canvas.getContext('2d',{alpha:false}),viewport,background:'rgb(255,255,255)'}).promise.then(()=>{if(!destroyed){entry.button.prepend(canvas);entry.rendered=true;entry.button.classList.add('is-rendered');}});
   }).catch(()=>{}).finally(()=>{entry.rendering=false;thumbBusy--;scheduleThumb();});
  }
 }
 function buildThumbnails(){
  if(thumbsBuilt||!pdf||!thumbList)return;thumbsBuilt=true;
  const fragment=document.createDocumentFragment();
  const entries=[];
  for(let number=1;number<=total();number++){
   const button=document.createElement('button');button.type='button';button.dataset.page=number;button.className='reader-thumbnail';button.setAttribute('aria-label','Go to page '+number);const label=document.createElement('span');label.textContent=number;button.append(label);button.addEventListener('click',()=>{showPage(number);stage.focus({preventScroll:true});});fragment.append(button);entries.push({button,number,rendered:false,rendering:false});
  }
  thumbList.append(fragment);
  if('IntersectionObserver'in window){observer=new IntersectionObserver(changes=>{for(const change of changes)if(change.isIntersecting){const entry=entries.find(entry=>entry.button===change.target);if(entry&&!entry.rendered){thumbQueue.push(entry);observer.unobserve(change.target);}}scheduleThumb();},{root:thumbnails,rootMargin:'180px'});entries.forEach(entry=>observer.observe(entry.button));}
  else{thumbQueue.push(...entries);scheduleThumb();}
  syncControls();
 }
 controls.prev?.addEventListener('click',()=>navigate(-1));controls.next?.addEventListener('click',()=>navigate(1));
 controls.page?.addEventListener('change',goToInput);controls.page?.addEventListener('keydown',event=>{if(event.key==='Enter'){event.preventDefault();goToInput();stage.focus({preventScroll:true});}});
 controls.progress?.addEventListener('change',event=>showPage(event.target.value));
 controls.progress?.addEventListener('input',event=>{const value=core.clampPage(event.target.value,total());event.target.setAttribute('aria-valuetext','Page '+value+' of '+total());});
 controls.mode?.addEventListener('change',event=>{mode=event.target.value;showPage(currentPage);});
 controls.zoomIn?.addEventListener('click',()=>{zoom=core.zoomLevel(zoom+.25);showPage(currentPage);});controls.zoomOut?.addEventListener('click',()=>{zoom=core.zoomLevel(zoom-.25);showPage(currentPage);});controls.fit?.addEventListener('click',()=>{zoom=1;showPage(currentPage);});
 controls.thumbsToggle?.addEventListener('click',()=>{thumbnails.hidden=!thumbnails.hidden;controls.thumbsToggle.setAttribute('aria-expanded',String(!thumbnails.hidden));if(!thumbnails.hidden){buildThumbnails();scheduleThumb();}requestAnimationFrame(()=>showPage(currentPage));});
 controls.fullscreen?.addEventListener('click',async()=>{try{if(document.fullscreenElement)await document.exitFullscreen();else await shell.requestFullscreen();}catch{message('Full screen is unavailable in this browser. The reader remains available on this page.');}});
 document.addEventListener('fullscreenchange',()=>{controls.fullscreen?.setAttribute('aria-pressed',String(Boolean(document.fullscreenElement)));setTimeout(()=>showPage(currentPage),60);});
 shell.addEventListener('keydown',event=>{if(event.defaultPrevented||event.ctrlKey||event.metaKey||event.altKey||event.target.closest('input,textarea,select,[contenteditable="true"],details'))return;if(event.key==='ArrowRight'){event.preventDefault();navigate(1);}if(event.key==='ArrowLeft'){event.preventDefault();navigate(-1);}});
 window.addEventListener('hashchange',()=>showPage(core.pageFromHash(location.hash,total()),{hash:false}));
 const resized=()=>{clearTimeout(resizeTimer);resizeTimer=setTimeout(()=>showPage(currentPage),140);};
 window.addEventListener('resize',resized);wide.addEventListener?.('change',resized);
 window.addEventListener('pagehide',event=>{if(event.persisted)return;destroyed=true;abortRender();observer?.disconnect();loadTask?.destroy().catch(()=>{});});
 Object.values(controls).forEach(control=>{if(control)control.disabled=true;});setBusy(true);
 try{
  const response=await fetch(root.dataset.manifest);if(!response.ok)throw new Error('Manifest unavailable');manifest=await response.json();
  const pdfURL=new URL(manifest.pdf_url,location.href);if(!/^https?:$/.test(pdfURL.protocol))throw new Error('Invalid PDF URL');
  const fallback=get('fallback');if(fallback)fallback.href=pdfURL.href;
  const pdfjs=await import('./vendor/pdfjs/pdf.mjs');pdfjs.GlobalWorkerOptions.workerSrc=new URL('./vendor/pdfjs/pdf.worker.mjs',import.meta.url).href;
  const options={url:pdfURL.href,cMapUrl:new URL('./vendor/pdfjs/cmaps/',import.meta.url).href,cMapPacked:true,standardFontDataUrl:new URL('./vendor/pdfjs/standard_fonts/',import.meta.url).href,wasmUrl:new URL('./vendor/pdfjs/wasm/',import.meta.url).href,iccUrl:new URL('./vendor/pdfjs/icc/',import.meta.url).href,isEvalSupported:false};
  loadTask=pdfjs.getDocument(options);loadTask.onProgress=progress=>{if(progress.total)message('Opening publication · '+Math.round(progress.loaded/progress.total*100)+'%');};pdf=await loadTask.promise;
  Object.values(controls).forEach(control=>{if(control)control.disabled=false;});
  if(controls.fullscreen&&!shell.requestFullscreen){controls.fullscreen.hidden=true;}
  currentPage=core.pageFromHash(location.hash,pdf.numPages);await showPage(currentPage,{hash:false});shell.classList.add('reader-ready');
 }catch(error){setBusy(false);shell.classList.add('reader-failed');message('The in-site reader could not open this publication. Use the original PDF or repository record below.');}
}
