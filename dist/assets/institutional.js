'use strict';
// Keep the collection context visible on desktop and compact on small screens.
const treePanel=document.getElementById('collection-tree-panel');
if(treePanel){const compact=matchMedia('(max-width: 1100px)');const syncTree=()=>{treePanel.open=!compact.matches;treePanel.dataset.treeReady='true';};syncTree();compact.addEventListener('change',syncTree);}
const enquiry=document.getElementById('enquiry-reference');
if(enquiry){const reference=new URLSearchParams(location.search).get('reference');if(reference)enquiry.value=reference;}
document.querySelectorAll('[data-live-filter]').forEach(input=>input.addEventListener('input',()=>{const value=input.value.normalize('NFKD').toLowerCase();const selector=input.dataset.liveFilter;let count=0;document.querySelectorAll(selector).forEach(row=>{row.hidden=!row.textContent.normalize('NFKD').toLowerCase().includes(value);count+=!row.hidden;});const status=document.getElementById(input.dataset.filterStatus);if(status)status.textContent=count+' matching records';}));
