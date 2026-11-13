"""Research context and a persistent collection tree for all archive records."""
from html import escape
from pathlib import PurePosixPath
from urllib.parse import quote
from publication_arrangement import collection_link
import json,re
E=lambda value:escape(str(value or ''),quote=True)

def collection_tree(path,records,programmes):
 base='../' if '/' in path else '';current=next((r for r in records if str(r['id'])==PurePosixPath(path).stem),None)
 groups=list(dict.fromkeys(r['collection'] for r in records));parts=sum(len(r.get('contents') or []) for r in records)
 tree=f'<aside class="collection-tree" aria-label="Archive navigation"><details id="collection-tree-panel" open><summary>Browse the archive<span>{len(records):02d} deposited editions · {parts:02d} analytic parts</span></summary><nav aria-label="Collection tree"><a class="tree-root" href="{base}finding-aid.html">Museum of One<br>Digital Archive Library</a><div class="tree-branch"><a href="{base}catalogue.html">Full catalogue</a>'
 for group in groups:
  rows=[r for r in records if r['collection']==group];active=current and current['collection']==group
  tree+=f'<details class="tree-group"'+(' open' if active else '')+f'><summary>{E(group)}<small>{len(rows)} deposited editions</small></summary><ul>'
  for r in rows:
   tree+=f'<li><a href="{base}items/{r["id"]}.html"'+(' aria-current="page"' if current and current['id']==r['id'] else '')+f'><span>{E(r["accession"])}</span>{E(r.get("short_title") or r["title"])}</a></li>'
  tree+=f'</ul><p><a href="{base}{E(collection_link(group))}">Browse the full collection ↗</a></p></details>'
 tree+='</div><div class="tree-tools">'
 for dest,label in [('research-discovery.html','Discover across the archive'),('contents.html','Chapters & essays'),('people.html','People & organisations'),('artworks.html','Artworks discussed'),('exhibitions.html','Exhibition context'),('research-registry.html','PIRR research records'),('programmes.html','Research pathways'),('vocabulary.html','Discovery vocabulary'),('policies.html','Policies & description'),('stewardship.html','Digital stewardship'),('research-help.html','Research enquiries')]:
  tree+=f'<a href="{base}{dest}"'+(' aria-current="page"' if path==dest else '')+f'>{label}</a>'
 tree+='</div><p class="tree-note">Published items and analytic parts. Editorial arrangement is described in the finding aid.</p></nav></details></aside>'
 return tree

def context_section(r,base):
 links=r.get('entity_links',[]);contents=r.get('contents',[]);terms=r.get('controlled_subjects',[])
 from pirr import pirr_item_panel
 section=pirr_item_panel(r,base=base)+'<section class="item-section" id="linked-context"><div class="section-no">Relationships / Named entities / Research access</div><h2>People, art & exhibition context</h2><p>Relationships describe a person or subject’s role in this document. Artworks discussed are not represented as objects held by the archive.</p>'
 if links:
  section+='<dl class="linked-entities">'
  for entity in links:
   id=entity.get('id');label=entity.get('label') or entity.get('name');relation=entity.get('relation_label') or entity.get('relation') or 'Related entity'
   section+=f'<div><dt>{E(relation.replace("_"," "))}</dt><dd><a href="{base}entities/{E(id)}.html">{E(label)} ↗</a><small>{E(entity.get("note"))}</small>'
   if entity.get('source_url'):section+=f'<a class="context-evidence" href="{E(entity["source_url"])}">Relationship source ↗</a>'
   section+='</dd></div>'
  section+='</dl>'
 else:section+='<p>Named-entity relationships have not been assigned to this record. The source descriptions remain available for review.</p>'
 section+='</section>'
 if contents:
  section+='<section class="item-section" id="analytic-contents"><div class="section-no">Analytic description / Parts of this edition</div><h2>Contents & component records</h2><p>Chapter and essay titles were checked against the deposited file. PDF file pages include covers and may differ from printed pagination. Component descriptions do not have independent repository deposits or DOIs.</p><ol class="contents-register">'
  for c in contents:
   start=c.get('pdf_start');end=c.get('pdf_end');span=str(start)+(('–'+str(end)) if end and end!=start else '')
   url=c.get('url') or f'parts/{r["id"]}-{c["id"]}.html';reader=c.get('reader_url') or f'read/{r["id"]}.html#page={start}'
   section+=f'<li><div><span class="catalogue-id">{E(c.get("reference"))}</span><a href="{base}{E(url)}">{E(c["title"])}</a></div><span><a href="{base}{E(reader)}">PDF pp. {E(span)} ↗</a></span></li>'
  section+='</ol></section>'
 if terms:
  section+='<section class="item-section" id="controlled-discovery"><div class="section-no">Preferred terms / Local vocabulary</div><h2>Controlled discovery terms</h2><p>These terms use the archive’s published definitions and preferred labels. Source keywords remain separately transcribed.</p><div class="controlled-terms">'
  for term in terms:
   id=term.get('id');label=term.get('label') or term.get('prefLabel') or term.get('preferred_label')
   section+=f'<a class="pill" href="{base}vocabulary.html#{E(id)}">{E(label)} ↗</a>'
  section+='</div></section>'
 return section

def responsibility_section(r):
 from policies import policy_record_panel
 return policy_record_panel(r,base='../').replace('id="description-history"','id="description-control"')

def institutional_page(path,html,records,programmes):
 base='../' if '/' in path else ''
 html=html.replace('</head>',f'<link rel="stylesheet" href="{base}assets/institutional.css"><script defer src="{base}assets/institutional.js"></script></head>')
 if path != 'index.html':
  html=re.sub(r'(<main id="main" class="shell">)(.*?)(</main>)',lambda m:m[1]+'<div class="archive-workspace">'+collection_tree(path,records,programmes)+'<div class="archive-workbench">'+m[2]+'</div></div>'+m[3],html,count=1,flags=re.S)
 if path=='programmes.html':
  for programme in programmes:
   if programme.get('pirr_registry_url'):
    heading='<h2>'+E(programme['title'])+'</h2>'
    ids=' · '.join(E(programme.get(k)) for k in ['pirr_reference','pirr_project_id'] if programme.get(k))
    badge='<div class="pirr-programme-reference"><a href="'+E(programme['pirr_registry_url'])+'">PIRR research record ↗</a>'+('<code>'+ids+'</code>' if ids else '')+'</div>'
    html=html.replace(heading,heading+badge,1)
 if path.startswith('items/'):
  r=next((r for r in records if str(r['id'])==PurePosixPath(path).stem),None)
  if r:
   html=html.replace('<section class="item-section" id="research-context">',context_section(r,base)+'<section class="item-section" id="research-context">',1)
   html=html.replace('<section class="item-section" id="files-record">',responsibility_section(r)+'<section class="item-section" id="files-record">',1)
   html=html.replace('<a href="#research-context">Research context ↓</a>',('<a href="#pirr-context">PIRR records ↓</a>' if r.get('pirr_references') else '')+'<a href="#linked-context">People & art ↓</a>'+('<a href="#analytic-contents">Contents ↓</a>' if r.get('contents') else '')+'<a href="#research-context">Research context ↓</a>')
   html=html.replace('<a href="#metadata-evidence">Inside the record ↓</a>','<a href="#metadata-evidence">Inside the record ↓</a><a href="#description-control">Description control ↓</a>')
 html=html.replace(f'<a href="{base}sources.html">Sources & authority records</a>',f'<a href="{base}people.html">People, art & events</a><a href="{base}policies.html">Policies & responsibilities</a><a href="{base}research-help.html">Research assistance</a><a href="{base}stewardship.html">Stewardship & integrity</a><a href="{base}sources.html">Sources & authority records</a>')
 return html
