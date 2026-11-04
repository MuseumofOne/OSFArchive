/* Small deterministic pagination helpers, shared by the reader and its tests. */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else root.ReaderCore=api;})(typeof globalThis!=='undefined'?globalThis:this,function(){
'use strict';
function clampPage(value,total){const max=Math.max(1,Math.floor(Number(total)||1));return Math.max(1,Math.min(max,Math.floor(Number(value)||1)));}
function spreadStart(page,total){const value=clampPage(page,total);return value===1?1:value-(value%2);}
function pagesFor(page,total,mode='single'){const value=clampPage(page,total);if(mode!=='spread')return [value];const start=spreadStart(value,total);return start===1?[1]:start<total?[start,start+1]:[start];}
function nextPage(page,total,mode='single'){const visible=pagesFor(page,total,mode);if(visible.at(-1)>=total)return visible[0];return mode==='spread'?(visible[0]===1?2:visible[0]+2):visible[0]+1;}
function previousPage(page,total,mode='single'){const visible=pagesFor(page,total,mode);return mode==='spread'?Math.max(1,visible[0]-2):Math.max(1,visible[0]-1);}
function pageFromHash(hash,total){const match=String(hash||'').match(/(?:^#|[&])page=(\d+)(?:&|$)/);return clampPage(match?match[1]:1,total);}
function fitScale(dimensions,width,height,gap=8){if(!Array.isArray(dimensions)||!dimensions.length)return 1;const w=Math.max(100,Number(width)||100),h=Math.max(100,Number(height)||100);const sum=dimensions.reduce((n,d)=>n+Math.max(1,d.width),0);const max=Math.max(...dimensions.map(d=>Math.max(1,d.height)));return Math.max(.05,Math.min((w-gap*(dimensions.length-1))/sum,h/max));}
function zoomLevel(value){return Math.max(1,Math.min(3,Math.round((Number(value)||1)*4)/4));}
return {clampPage,spreadStart,pagesFor,nextPage,previousPage,pageFromHash,fitScale,zoomLevel};
});
