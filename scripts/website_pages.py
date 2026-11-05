"""Render source web records separately from the curated publication catalogue."""
from pathlib import Path
from html import escape,unescape
import hashlib,json,shutil,re
from website_sync import digest,encoded

def build_website_pages(work,out,write,layout,origin):
 work=Path(work);out=Path(out)
 # A fresh whitelist is rebuilt each time, never leave a withdrawn readable file.
 for p in [out/'website',out/'assets/website-captures']:
  if p.exists():shutil.rmtree(p)
 current=json.loads((work/'public/current.json').read_text()) if (work/'public/current.json').exists() else []
 source_map={p['source']['url']:origin+'/website/'+p['archive_id']+'.html' for p in current}
 fragment_map={p['source']['url']:set(re.findall(r'id="([^"]+)"',p['readable_html'])) for p in current}
 report=json.loads((work/'report.json').read_text()) if (work/'report.json').exists() else {'mode':'not_reconciled','eligible_records':0}
 e=lambda x:escape(str(x or ''),quote=True);paths=[];metadata=[]
 intro='<div class="page-head"><div class="eyebrow">Website record / Automatic capture</div><h1>The published website, held in the archive.</h1><p>Public posts and pages, including essays, research, books’ web descriptions and public tool pages. Website records remain distinct from deposited publication editions.</p></div>'
 intro+='<div class="reading"><p>Reconciliation: '+e(report.get('checked_at','Not yet run'))+' · '+e(len(current))+' current readable web captures. Earlier revisions are retained as encrypted recovery objects, not overwritten.</p><p><a href="metadata/website-sync.json">Reconciliation report</a> · <a href="metadata/website-captures.json">Capture metadata</a></p><ul class="source-list">'
 for p in current:
  r=p['source'];rid=p['archive_id'];page='website/'+rid+'.html';url=origin+'/'+page
  intro+='<li><a href="'+page+'">'+e(r['title'])+'</a><small>'+e(r['kind'])+' · Website publication '+e(p['original_published_at'])+'</small></li>'
  assets=[];replacements={}
  for a in p['attachments']:
   a=dict(a);path=a.get('archive_path')
   if a['storage']=='local_archival_file':
    file=work/'public'/path
    if not file.is_file() or digest(file.read_bytes())!=a['sha256']:raise ValueError('Capture asset checksum mismatch')
    target=out/path;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(file,target)
   if path:replacements[a['url']]=origin+'/'+path
   assets.append(a)
  body=p['readable_html']
  for source,target in {**source_map,**replacements}.items():body=body.replace('href="'+e(source)+'"','href="'+e(target)+'"')
  for source,target in source_map.items():
   body=re.sub('href="'+re.escape(e(source))+'#([^"]+)"',lambda m:'href="'+e(target)+'#'+m[1]+'"' if unescape(m[1]) in fragment_map[source] else m[0],body)
  stored=( '<!doctype html><html lang="'+e(p.get('language') or 'und')+'"><head><meta charset="utf-8"><title>'+e(r['title'])+'</title></head><body><h1>'+e(r['title'])+'</h1>'+body+'</body></html>').encode()
  raw=(r['html'] or '').encode();capture_files=[{'path':page,'role':'Readable web capture','bytes':len(stored),'sha256':digest(stored)},{'path':'website/'+rid+'.source.html.txt','role':'Original published content HTML, inert source download','bytes':len(raw),'sha256':digest(raw)}]
  rawpath=out/capture_files[1]['path'];rawpath.parent.mkdir(exist_ok=True,parents=True);rawpath.write_bytes(raw)
  # Self-canonical wrapper is the catalogue record; inert text download avoids
  # executing authored app code or third-party widgets in the archive origin.
  fields=[('Source publication',p['original_published_at']),('Current source publication field',r['published_at']),('Source modified',r['updated_at']),('First archive capture',p['first_captured_at']),('Selected capture',p['capture']['captured_at']),('Revision count',p['revision_count']),('Language',p.get('language') or 'Not explicitly supplied'),('Source role',r['kind']+' on the website; no book/edition identity inferred')]
  content='<div class="website-record"><div class="page-head"><div class="eyebrow">Website capture / '+e(rid)+'</div><h1>'+e(r['title'])+'</h1><p>'+e(p['summary'])+'</p><p><a href="'+e(r['url'])+'">Canonical website source ↗</a> · <a href="../website-records.html">All website captures</a> · <a href="'+rid+'.source.html.txt" download>Original content HTML ↓</a></p></div><div class="reading"><dl class="metadata">'
  content+=''.join('<div><dt>'+e(k)+'</dt><dd>'+e(v)+'</dd></div>' for k,v in fields)+'</dl>'
  content+='<h2>Credited website creators</h2><p>'+e('; '.join(x['name']+' ('+x['role']+')' for x in r['creators']) or 'Not supplied')+'</p>'
  content+='<h2>Rights and access</h2><p>This is a stored copy of a public website publication, captured under the website owner’s archive instruction. Original source rights, image credits, citations and third-party exclusions remain applicable. Public access does not grant a new licence. External embeds and unpreserved files are explicitly identified below. Interactive source is retained as an inert HTML download; a live software environment is not guaranteed.</p>'
  if r.get('feature_image_caption'):
   from website_sync import Readable
   content+='<h2>Source feature-image credit</h2>'+''.join(Readable(r['feature_image_caption']).parts)
  content+='<h2>Published content</h2><section class="website-captured-content">'+body+'</section>'
  content+='<h2>Files, images and media</h2><ul class="source-list">'
  for a in assets:
   target=origin+'/'+a['archive_path'] if a.get('archive_path') else a['url'];label=a.get('label') or a['url'].split('/')[-1]
   content+='<li><a href="'+e(target)+'">'+e(label)+'</a><small>'+e(a['storage'].replace('_',' '))+' · '+e(a['availability'])+'</small><small>'+e(a['reason'])+'</small>'
   if a.get('sha256'):content+='<small>'+e(a.get('bytes'))+' bytes · SHA-256 '+e(a['sha256'])+'</small>'
   if a.get('archive_path') and (a.get('mime_type') or '').startswith('image/'):
    content+='<img loading="lazy" style="max-width:100%;height:auto" src="'+e(target)+'" alt="'+e(label)+'">'
   if a.get('archive_path') and (a.get('mime_type') or '').startswith(('audio/','video/')):
    tag='audio' if a['mime_type'].startswith('audio/') else 'video'
    content+='<'+tag+' controls preload="none" src="'+e(target)+'">'+e(label)+'</'+tag+'>'
   content+='</li>'
  content+='</ul><h2>Source-declared metadata</h2><p>Transcribed declarations retain their source scope. Identifiers are not promoted to independently verified edition assignments.</p><dl class="metadata">'
  content+=''.join('<div><dt>'+e(v['name'])+'</dt><dd>'+e(v['content'])+'</dd></div>' for v in r['source_declared_metadata'])+'</dl>'
  content+='<p>Source content SHA-256: <code>'+e(p['capture']['content_hash'])+'</code></p>'
  if p['validation_issues']:content+='<h2>Fields requiring qualification</h2><ul>'+''.join('<li>'+e(v)+'</li>' for v in p['validation_issues'])+'</ul>'
  content+='</div></div>'
  schema={'@context':'https://schema.org','@type':'WebPage','@id':url+'#record','url':url,'name':r['title'],'description':p['summary'],'dateCreated':p['first_captured_at'],'dateModified':p['capture']['captured_at'],'isBasedOn':{'@type':'WebPage','@id':r['url'],'url':r['url'],'datePublished':r['published_at'],'dateModified':r['updated_at']},'isPartOf':{'@id':origin+'/#website'}}
  html=layout(r['title'],p['summary'] or 'Stored public website record and its source metadata.',content,page,base='../',schema=schema)
  html=html.replace('</head>','<link rel="stylesheet" href="../assets/website-captures.css"></head>')
  write(page,html);paths.append(page)
  # Hash final generated presentation and original inert source separately.
  capture_files[0].update(bytes=(out/page).stat().st_size,sha256=digest((out/page).read_bytes()))
  metadata.append({k:v for k,v in p.items() if k not in ('readable_html','text')} | {'source':{k:v for k,v in r.items() if k!='html'},'files':capture_files,'url':url})
 intro+='</ul></div>';write('website-records.html',layout('Website captures','Automatically captured public Museum of One website records and uploaded files.',intro,'website-records.html'));paths.append('website-records.html')
 write('metadata/website-captures.json',json.dumps(metadata,ensure_ascii=False,indent=2));write('metadata/website-sync.json',json.dumps(report,ensure_ascii=False,indent=2))
 return paths
