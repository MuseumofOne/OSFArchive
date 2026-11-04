"""Presentation and progressive enhancement for the archival reading room."""
from html import escape
from pathlib import Path
import json,re,urllib.parse
E=lambda x:escape(str(x or ''),quote=True)

def discovery_payload(records):
 keys=['id','accession','title','short_title','author','date','date_precision','type','collection','summary','subjects','doi','conceptdoi','isbn','language','medium','digital_formats','extent','cover','cover_alt','license','institutional_url','zenodo_url','research_programmes','edition_statement','first_edition']
 return [{k:r.get(k) for k in keys} for r in records]

def dialogs(base):
 return '''<dialog class="archive-dialog" id="reading-dialog" aria-labelledby="reading-heading"><div class="dialog-head"><div><span class="eyebrow">Your research desk</span><h2 id="reading-heading">The reading list</h2></div><button type="button" class="dialog-close" data-close-dialog aria-label="Close reading list">×</button></div><div class="dialog-body"><p class="dialog-intro">Keep a small shelf of records to return to. Saved in this browser; no account or synchronization.</p><p id="reading-message" role="status"></p><div id="reading-records"></div><div class="reading-actions"><button type="button" class="button" id="compare-records" disabled>Compare selected records</button><button type="button" class="button outline" id="export-reading">Export list · CSV ↓</button><button type="button" class="text-button" id="clear-reading">Clear list</button></div><p class="dialog-footnote">Select two or three saved records to compare editions, identifiers, rights, and research context.</p></div></dialog>
<dialog class="archive-dialog comparison-dialog" id="comparison-dialog" aria-labelledby="comparison-heading"><div class="dialog-head"><div><span class="eyebrow">Side by side</span><h2 id="comparison-heading">Compare the records</h2></div><button type="button" class="dialog-close" data-close-dialog aria-label="Close comparison">×</button></div><div class="dialog-body" id="comparison-content"></div></dialog>
<dialog class="archive-dialog lightbox-dialog" id="cover-dialog" aria-labelledby="cover-heading"><div class="dialog-head"><h2 id="cover-heading">Publication cover</h2><button type="button" class="dialog-close" data-close-dialog aria-label="Close cover view">×</button></div><figure class="cover-figure"><img id="cover-image" alt=""><figcaption id="cover-caption"></figcaption></figure></dialog><div class="archive-toast" id="archive-toast" role="status" aria-live="polite"></div>'''

def provenance_section(r):
 assertions=r.get('field_assertions',[])
 # build_assertions is generated centrally to keep UI and exports in agreement.
 from metadata import build_assertions
 assertions=build_assertions(r)
 content='<section class="item-section" id="metadata-evidence"><div class="section-no">Description / Sources / Interpretation</div><h2>Inside the record</h2><p>Inspect how this description was assembled. Source transcription, institutional context, and catalogue interpretation remain distinct.</p>'
 alt=r.get('alternate_titles',[])
 if alt:
  content+='<details class="metadata-disclosure"><summary>Title variants & parallel descriptions</summary><ul class="source-list">'
  for a in alt:content+=f'<li>{E(a.get("title"))}<small>{E(a.get("kind", "Source title"))}'+(f' · <a href="{E(a["source_url"])}">Source ↗</a>' if a.get('source_url') else '')+'</small></li>'
  content+='</ul></details>'
 validation=r.get('identifier_validation',{})
 if validation:
  content+='<details class="metadata-disclosure"><summary>Identifier integrity & scope</summary><p>Check-digit validation tests an identifier’s structure. It does not establish agency registration, a library holding, or applicability to every edition.</p><ul class="source-list">'
  for kind,entries in validation.items():
   if isinstance(entries,dict):entries=[entries]
   if not isinstance(entries,list):continue
   for a in entries:
    if not isinstance(a,dict):continue
    value=a.get('source_value') or a.get('value') or a.get('normalized')
    if not value:continue
    content+=f'<li><strong>{E(kind.upper())}</strong> · {E(value)}'
    if a.get('normalized') and a['normalized']!=value:content+=f'<small>Normalized form: {E(a["normalized"])}</small>'
    if a.get('syntax_valid') is not None:content+=f'<small>Syntax: {"valid" if a["syntax_valid"] else "does not validate"}</small>'
    if a.get('checksum_valid') is not None:content+=f'<small>Check digit: {"valid" if a["checksum_valid"] else "does not validate"}</small>'
    content+=f'<small>{E(a.get("scope"))}</small><small>{E(a.get("note"))}</small></li>'
  content+='</ul></details>'
 if r.get('contributor_roles'):
  content+='<details class="metadata-disclosure"><summary>Repository responsibility statements</summary><ul class="source-list">'
  for c in r['contributor_roles']:
   content+=f'<li>{E(c.get("name"))}<small>{E(c.get("role_label") or c.get("role") or c.get("source_role") or c.get("type") or "Source creator")}</small></li>'
  content+='</ul><p>These are roles as supplied by the repository. They are not inferred authorship or peer-review claims.</p></details>'
 content+='<details class="metadata-disclosure"><summary>Field-level provenance ledger</summary><label class="evidence-filter">Show fields <select id="evidence-filter"><option value="">All description layers</option><option value="source">Repository source</option><option value="institutional">Institutional context</option><option value="editorial">Editorial / derived description</option></select></label><div class="table-scroll"><table class="assertion-table"><thead><tr><th scope="col">Field</th><th scope="col">Description layer</th><th scope="col">Evidence</th></tr></thead><tbody>'
 for a in assertions:
  status=a.get('status',''); category='editorial' if any(x in status for x in ['editorial','derived','catalogue']) else 'institutional' if 'institutional' in status else 'source'
  label={'source':'Repository source','institutional':'Institutional context','editorial':'Catalogue description'}[category]
  content+=f'<tr data-evidence-status="{category}"><th scope="row">{E(a.get("field", "").replace("_", " ").capitalize())}</th><td><span class="evidence-badge {category}">{label}</span></td><td>'
  if a.get('source_url'):content+=f'<a href="{E(a["source_url"])}">Source ↗</a>'
  else:content+='Local catalogue'
  if a.get('note'):content+=f'<small>{E(a["note"])}</small>'
  content+='</td></tr>'
 content+='</tbody></table></div></details></section>'
 return content

def enhance_page(path,html,records,programmes):
 base='../' if '/' in path else ''
 lookup={str(r['id']):r for r in records}
 html=html.replace('<body>',f'<body data-root="{base}" data-page="{E(path)}">')
 html=html.replace(f'<script defer src="{base}assets/app.js">',f'<script defer src="{base}assets/archive-core.js"></script><script defer src="{base}assets/app.js">')
 html=html.replace('<a class="nav-search"', '<button type="button" class="reading-list-button" data-open-reading aria-label="Open reading list">Reading list <span data-reading-count>0</span></button><a class="nav-search"')
 def enhance_card(m):
  target,attrs,inner=m.groups();rid=Path(urllib.parse.urlparse(target).path).stem;r=lookup.get(rid)
  if not r:return m.group(0)
  inner=inner.replace('</h3>','</h3><p class="card-abstract">'+E(r['summary'])+'</p>',1)
  return f'<article class="catalogue-card"{attrs}><a class="book-card" href="{E(target)}">{inner}</a><div class="record-tools"><span class="record-collection">{E(r["type"])}</span><button type="button" class="save-record" data-save="{E(rid)}" aria-pressed="false" aria-label="Save {E(r["short_title"])} to reading list"><span aria-hidden="true">＋</span> Save</button></div></article>'
 html=re.sub(r'<a class="book-card" href="([^"]+)"([^>]*)>(.*?)</a>',enhance_card,html,flags=re.S)
 if path=='catalogue.html':
  html=html.replace('<div class="result-toolbar">','<div class="active-filters" id="active-filters" aria-label="Active filters"></div><div class="result-toolbar">')
  html=html.replace('<span id="result-count" aria-live="polite">','<div class="view-switch" role="group" aria-label="Catalogue view"><button type="button" data-view="grid" aria-pressed="true">Shelf</button><button type="button" data-view="list" aria-pressed="false">List</button></div><span id="result-count" aria-live="polite">')
  html=html.replace('id="catalogue-grid"','id="catalogue-grid" data-view="grid"')
  html=html.replace('placeholder="Search titles, subjects, identifiers…"','placeholder="Search titles, subjects, item numbers, identifiers…"')
 if path=='index.html':
  html=html.replace('<section class="hero">','<div class="archive-masthead"><span class="archive-masthead-title">Digital Archive Library</span><span class="archive-masthead-aside">Museum of One / Catalogue edition 02</span></div><section class="hero">',1)
  html=html.replace('A quiet place<br>for <em>the record.</em>','The record.<br><em>In context.</em>')
  html=html.replace('Published thought, carefully held.<br>Explore the books, treatises, and critical writing of Museum of One through a source-linked archival catalogue.','A reading room for published thought.<br>Follow a work from its first edition to the questions it continues to open.')
  html=html.replace('<div class="actions"><a class="button" href="catalogue.html">','<form class="home-search" action="catalogue.html"><label class="sr-only" for="home-query">Search the digital archive library</label><input id="home-query" name="q" type="search" placeholder="Begin with a title, idea, or identifier…"><button type="submit" aria-label="Search the archive">↗</button></form><div class="actions"><a class="button" href="catalogue.html">',1)
  books=[r for r in records if r.get('cover')][:4]
  if books:
   r=books[0]
   new=f'<div class="hero-art"><span class="shelf-label">ON THE READING DESK / SELECTED EDITIONS</span><span class="hero-shelf-number" aria-hidden="true">I</span><div class="hero-cover-mat"><a id="hero-record-link" href="items/{r["id"]}.html"><img id="hero-cover" class="hero-featured-cover" src="{E(r["cover"])}" alt="{E(r["cover_alt"])}" fetchpriority="high"></a></div></div><div class="hero-switcher" role="group" aria-label="Featured publications">'
   for i,book in enumerate(books):new+=f'<button type="button" data-featured="{E(book["id"])}" aria-pressed="{str(i==0).lower()}" aria-label="Show {E(book["short_title"])}">{["I","II","III","IV"][i]}</button>'
   new+=f'<a class="hero-selected-caption" id="hero-selected-caption" href="items/{r["id"]}.html">{E(r["short_title"])} <span aria-hidden="true">↗</span></a></div>'
   html=re.sub(r'<div class="hero-art">.*?<div class="hero-caption">.*?</div>',new,html,count=1,flags=re.S)
 if path.startswith('items/'):
  r=lookup.get(Path(path).stem)
  if r:
   html=html.replace('<a class="text-link" href="#bibliographic-record">Explore the record ↓</a>',f'<button type="button" class="button outline save-record" data-save="{E(r["id"])}" aria-pressed="false">＋ Save to reading list</button>')
   if r.get('cover'):
    html=html.replace('<div class="cover-well"><img',f'<button type="button" class="cover-well cover-open" data-cover-src="{E(base+r["cover"])}" data-cover-caption="{E(r["cover_alt"])}" aria-label="Enlarge publication cover"><img',1)
    html=html.replace('</div><div class="hero-caption"><span>PUBLICATION COVER','<span class="cover-zoom-label">View full cover ↗</span></button><div class="hero-caption"><span>PUBLICATION COVER',1)
   html=html.replace('<section class="item-section" id="files-record">',provenance_section(r)+'<section class="item-section" id="files-record">')
   html=html.replace('<a href="#source-evidence">Source evidence ↓</a>','<a href="#source-evidence">Source evidence ↓</a><a href="#metadata-evidence">Inside the record ↓</a>')
   html=html.replace('Date of this repository edition; not necessarily the first edition.',f'Source date precision: {E(r.get("date_precision", "as supplied"))}. Not necessarily the first edition.')
 html=html.replace('</body>',dialogs(base)+'</body>')
 return html
