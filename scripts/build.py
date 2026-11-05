"""Generate a portable, source-qualified static archive. Python catalogue with verified PDF text extraction."""
from metadata import build_graph, build_dc, build_assertions
from osf_editions import attach_osf_editions
from experience import enhance_page, discovery_payload
from enrich import enrich_record
from finding_aid import build_finding_aid
from entities import attach_entities, build_entity_pages, entity_graph
from contents import attach_contents, build_content_pages
from vocabulary import attach_vocabulary, build_vocabulary_pages
from policies import attach_catalogue_history, build_policy_pages
from stewardship import build_stewardship_page
from institutional import institutional_page
from pirr import load_pirr, attach_pirr, build_pirr_pages
from archival import archival_page
from readers import apply_reading_metadata, reader_link, build_reader_pages
from integration_search import build_search_index, encode_search_index, load_source_snapshots, public_export_eligible, searchable_text
from descriptions import repository_description_html
from relationship_assertions import relation_register, typed_entity_relationship_assertions
from quality_page import collect_graphs, build_quality_page
from citations import build_citation_model, visible_citation, csl_json, bibtex, ris, scholar_meta
from discovery_v2 import build_research_discovery, build_fulltext_index, build_discovery_page, encode_index
from pathlib import Path
from html import escape
import json, os, re, shutil, urllib.parse, xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'dist'; DATA=ROOT/'data'
ORIGIN=(os.environ.get('SITE_ORIGIN') or 'https://archive.museumofone.art').rstrip('/')
RECORDS=json.loads((DATA/'catalogue.json').read_text())
if isinstance(RECORDS,dict): RECORDS=RECORDS['records']
# This repository is a public catalogue, never a draft store. Fail before writing
# any artifact if a future record lacks explicit public source evidence.
SOURCE_SNAPSHOTS=load_source_snapshots(RECORDS,DATA/'source')
ineligible=[str(r.get('id','unknown')) for r in RECORDS if not public_export_eligible(r,SOURCE_SNAPSHOTS.get(str(r.get('id'))))]
if ineligible:raise ValueError('Catalogue contains records not eligible for public export: '+', '.join(ineligible))
from metadata_profile import PROFILE, prepare_metadata_records, build_quality_report, require_valid_report, combine_graphs, validate_metadata_profile
AUTHORITIES=json.loads((DATA/'authorities.json').read_text())
RECORDS=apply_reading_metadata([enrich_record(r,AUTHORITIES) for r in RECORDS],ROOT)
RECORDS=attach_osf_editions(RECORDS,ROOT)
ENTITIES=json.loads((DATA/'entities.json').read_text())
CONTENTS=json.loads((DATA/'contents.json').read_text())
VOCABULARY=json.loads((DATA/'vocabulary.json').read_text())
VOCABULARY['scheme']['base_uri']=ORIGIN+'/vocabulary.html'
RECORDS=attach_catalogue_history(attach_vocabulary(attach_contents(attach_entities(RECORDS,ENTITIES),CONTENTS),VOCABULARY))
for record in RECORDS:record['description_policy_url']=ORIGIN+'/policies.html'
E=lambda x:escape(str(x or ''),quote=True)
J=lambda x:json.dumps(x,ensure_ascii=False).replace('<','\\u003c')
TODAY='2026-11-05'
PROGRAMMES=json.loads((DATA/'programmes.json').read_text()) if (DATA/'programmes.json').exists() else []
PIRR=load_pirr()
RECORDS,PROGRAMMES=attach_pirr(RECORDS,PROGRAMMES,PIRR)
RECORDS=prepare_metadata_records(RECORDS,ORIGIN)
PROFILE_ERRORS=validate_metadata_profile(RECORDS,ORIGIN)
if PROFILE_ERRORS:raise ValueError("Metadata source profile failed: "+"; ".join(PROFILE_ERRORS))
def programme_id(p):return urllib.parse.urlparse(p['url']).path.strip('/').split('/')[-1]
def programmes_for(r):return r.get('research_programmes',[])
def programme_badges(r,base=''):
 return '<div class="programme-badges">'+''.join(f'<a class="programme-badge" href="{base}programmes.html#{E(programme_id(p))}">{E(p["title"])}<small>{E(p.get("status", "See programme"))}</small></a>' for p in programmes_for(r))+'</div>' if programmes_for(r) else ''

collection_config=json.loads((DATA/'collections.json').read_text())
GROUPS={c['name']:(f"{i+1:02d}",c['title'],c['description']) for i,c in enumerate(collection_config['collections'])}
for r in RECORDS:
 if r['collection'] not in GROUPS:GROUPS[r['collection']]=(f"{len(GROUPS)+1:02d}",r['collection'],'Explore records in this collection.')
SEARCH_ICON='<svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 5 5"/></svg>'

def url(path): return ORIGIN+'/' if path in ('', 'index.html') else ORIGIN+'/'+path.lstrip('/')
def href(path,base):return base+path

def header(base,active=''):
 return f'''<a class="skip" href="#main">Skip to content</a><div class="shell"><div class="utility"><a href="https://www.museumofone.art/">Museum of One / Research, criticism & preservation ↗</a><span>A source-linked digital catalogue · Selected works</span></div><header class="header"><a class="brand" href="{base}index.html"><img class="brand-seal" src="{base}assets/institution-seal.webp" alt=""><span><strong>Museum of One</strong><small>Digital Archive Library</small></span></a><nav class="nav" aria-label="Main navigation">'''+''.join(f'<a href="{base}{p}"'+(' aria-current="page"' if active==key else '')+f'>{label}</a>' for key,p,label in [('discovery','research-discovery.html','Discover'),('catalogue','catalogue.html','Catalogue'),('collections','collections.html','Collections'),('programmes','programmes.html','Research'),('about','about.html','About the archive')])+f'<a class="nav-search" href="{base}research-discovery.html">{SEARCH_ICON}<span>Search</span></a></nav></header></div>'
def footer(base):
 return f'''<div class="shell"><footer class="footer"><div class="footer-main"><div><h2>Museum of One</h2><p>An archival reading room for published work in aesthetics, art criticism, and the ethics of witnessing.</p></div><div class="footer-links"><div><a href="{base}catalogue.html">Browse the catalogue</a><a href="{base}collections.html">Explore collections</a><a href="{base}programmes.html">Research programmes</a><a href="{base}subjects.html">Subject index</a><a href="{base}about.html">About & metadata policy</a></div><div><a href="https://www.museumofone.art/">Museum of One ↗</a><a href="{base}sources.html">Sources & authority records</a><a href="{base}metadata-quality.html">Catalogue quality</a><a href="{base}website-records.html">Website captures</a><a href="{base}metadata/catalogue.json" download>Download catalogue JSON ↓</a></div></div></div><div class="footer-bottom"><span>© Museum of One · Individual works retain their own rights.</span><span>Selected catalogue · Source review {TODAY} · Persistent catalogue records</span></div></footer></div>'''
def layout(title,desc,content,path='index.html',base='',active='',schema=None):
 graph=schema or {'@context':'https://schema.org','@type':'CollectionPage','name':title,'description':desc,'url':url(path),'isPartOf':{'@type':'WebSite','@id':ORIGIN+'/#website','name':'Museum of One Digital Archive Library','url':ORIGIN+'/'}}
 return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{E(title)} | Museum of One Digital Archive Library</title><meta name="description" content="{E(desc[:170])}"><link rel="canonical" href="{E(url(path))}"><meta property="og:site_name" content="Museum of One Digital Archive Library"><meta property="og:locale" content="en_GB"><meta property="og:type" content="website"><meta name="twitter:card" content="summary"><meta property="og:title" content="{E(title)}"><meta property="og:description" content="{E(desc[:200])}"><meta property="og:url" content="{E(url(path))}"><meta name="theme-color" content="#f3f0e8"><link rel="icon" href="{base}assets/favicon.svg" type="image/svg+xml"><link rel="stylesheet" href="{base}assets/style.css"><script type="application/ld+json">{J(graph)}</script><script defer src="{base}assets/app.js"></script></head><body>{header(base,active)}<main id="main" class="shell">{content}</main>{footer(base)}</body></html>'''
def write(path,content):
 if path.endswith('.html') and path != '404.html':
  content=enhance_page(path,content,RECORDS,PROGRAMMES)
  content=archival_page(path,content,RECORDS,PROGRAMMES)
  content=reader_link(path,content,RECORDS)
  content=institutional_page(path,content,RECORDS,PROGRAMMES)
  design_base="../" if "/" in path else ""
  content=content.replace("</head>",f'<link rel="stylesheet" href="{design_base}assets/archival-design.css"></head>')
 p=OUT/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(content)
def cover(r,base='',hero=False):
 if r.get('cover'): return f'<img src="{base}{E(r["cover"])}" alt="{E(r.get("cover_alt") or "Published cover of "+r["title"])}" '+('fetchpriority="high"' if hero else 'loading="lazy"')+' decoding="async">'
 return f'<div class="cover-placeholder" aria-label="Catalogue display, not an original publication cover"><span class="cover-kicker">MUSEUM OF ONE<br>ARCHIVAL LIBRARY</span><span class="cover-title">{E(r.get("short_title",r["title"]))}</span><span class="cover-author">{E(r["author"])}<br>{E(r["date"][:4])} · Catalogue display</span></div>'
def card(r,base='',search=False):
 attrs=''
 if search:
  searchtext=searchable_text(r)
  attrs=f' data-programmes="{E(json.dumps([programme_id(p) for p in programmes_for(r)]))}" data-type="{E(r["type"])}" data-record data-title="{E(r["title"])}" data-search="{E(searchtext)}" data-group="{E(r["collection"])}" data-year="{E(r["date"][:4])}" data-date="{E(r["date"])}" data-subjects="{E(json.dumps(r["subjects"]))}"'
 return f'<a class="book-card" href="{base}items/{r["id"]}.html"{attrs}><div class="cover-well">{cover(r,base)}</div><div class="catalogue-id">{E(r["accession"])} <span class="arrow" aria-hidden="true">↗</span></div><h3>{E(r.get("short_title",r["title"]))}</h3><p>{E(r["author"])} · {E(r["date"][:4])}<br>{E(r["type"])}</p></a>'
def pagehead(eyebrow,title,desc):
 return f'<div class="page-head"><div class="breadcrumb"><a href="index.html">Library</a> / {E(eyebrow)}</div><div class="eyebrow">{E(eyebrow)}</div><h1>{E(title)}</h1><p>{E(desc)}</p></div>'

books=[r for r in RECORDS if r['collection']=='Books & volumes']
featured=(books+[r for r in RECORDS if r not in books])[:4]
withcovers=[r for r in RECORDS if r.get('cover')]
art=''
for i,r in enumerate(withcovers[:2]):
 art+=f'<img class="book {"second" if i else ""}" src="{E(r["cover"])}" alt="{E(r.get("cover_alt",r["title"]))}" fetchpriority="high">'
if not art:art=cover(RECORDS[0],hero=True)
hero=f'''<section class="hero"><div><div class="eyebrow">The digital archive / Selected works</div><h1>A quiet place<br>for <em>the record.</em></h1><p class="hero-copy">Published thought, carefully held.<br>Explore the books, treatises, and critical writing of Museum of One through a source-linked archival catalogue.</p><div class="actions"><a class="button" href="catalogue.html">Enter the catalogue <span aria-hidden="true">↗</span></a><a class="text-link" href="about.html">About this archive</a></div></div><div><div class="hero-art"><span class="shelf-label">MUSEUM OF ONE PRESS / THE COLLECTED SHELF</span>{art}</div><div class="hero-caption"><span>PUBLICATION COVERS / MUSEUM OF ONE</span><span>01 — 02</span></div></div></section><div class="hero-foot"><span>{len(RECORDS):02d} CATALOGUED RECORDS</span><span><span class="dot">●</span> SOURCE-LINKED EDITIONS</span><span>BOOKS · THEORY · CRITICAL WRITING</span></div>'''
selected=f'<section class="section"><div class="section-head"><div><span class="section-no">01 / The collected shelf</span><h2>Selected editions</h2></div><a class="text-link" href="catalogue.html">View all records ↗</a></div><div class="book-grid">'+''.join(card(r) for r in featured)+'</div></section>'
routes='<section class="section" style="padding-top:0"><div class="section-head"><div><span class="section-no">02 / Paths into the archive</span><h2>Follow a line of inquiry</h2></div></div><div class="route-grid">'
for group,(n,title,desc) in GROUPS.items():
 count=sum(r['collection']==group for r in RECORDS)
 routes+=f'<a class="route-card" href="catalogue.html?collection={urllib.parse.quote(group)}"><span class="route-top"><span>{n} / {E(group.upper())}</span><span>{count:02d} RECORDS</span></span><h3>{E(title)}</h3><p>{E(desc)}</p><span class="small-link">Explore the collection ↗</span></a>'
routes+='</div></section>'
recent='<section class="section recent"><div class="section-head"><div><span class="section-no">03 / Reading room</span><h2>From the catalogue</h2></div><a class="text-link" href="catalogue.html">Browse the reading room ↗</a></div>'
for r in [x for x in RECORDS if x not in featured][:4]:recent+=f'<a class="record-row" href="items/{r["id"]}.html"><span class="row-id">{E(r["accession"])}</span><span><h3>{E(r["title"])}</h3><p>{E(r["author"])} · {E(r["date"][:4])}</p></span><span class="row-type">{E(r["type"])}</span><span aria-hidden="true">↗</span></a>'
recent+='</section>'
note='''<section class="archive-note"><div><div class="eyebrow">A record, with its sources</div><h2>Preserve the work.<br>Keep its context.</h2></div><div><p>Every catalogue entry brings the deposited edition into conversation with its Museum of One publication record. Original metadata, editorial description, and external references remain distinct.</p><p>Read, cite, and follow the evidence back to its source.</p><a href="sources.html">Sources, identifiers & catalogue links ↗</a></div></section>'''
research_home='<section class="section" style="padding-top:0"><div class="section-head"><div><span class="section-no">Research / From inquiry to publication</span><h2>Stay with the inquiry.</h2></div><a class="text-link" href="programmes.html">Research programmes ↗</a></div><p style="max-width:650px;color:var(--muted);font-size:13px">Follow the programme badges into Museum of One’s continuing research. Published outputs retain their own records; programme stages remain distinct from publication status.</p><div class="programme-badges">'+''.join(f'<a class="programme-badge" href="programmes.html#{E(programme_id(p))}">{E(p["title"])}<small>{E(p.get("status", ""))}</small></a>' for p in PROGRAMMES if any(any(x['url']==p['url'] for x in programmes_for(r)) for r in RECORDS))+'</div></section>'
write('index.html',layout('The Archival Library','Explore Museum of One books, treatises and critical writing in a source-linked digital catalogue.',hero+selected+routes+research_home+recent+note))

subjects=sorted({s for r in RECORDS for s in r['subjects']});years=sorted({r['date'][:4] for r in RECORDS},reverse=True)
def options(values):return ''.join(f'<option value="{E(v)}">{E(v)}</option>' for v in values)
catalogue=pagehead('Catalogue','The published record.','Browse a selected corpus of Museum of One publications. Search titles, creators, subjects, ISBNs, and DOIs.')
catalogue+=f'''<div class="catalogue-layout"><aside class="filters" aria-label="Filter the catalogue"><h2 class="filter-title">Refine the catalogue</h2><div class="filter-field"><label for="group-filter">Collection</label><select id="group-filter"><option value="">All collections</option>{options(GROUPS)}</select></div><div class="filter-field"><label for="year-filter">Repository publication year</label><select id="year-filter"><option value="">All years</option>{options(years)}</select></div><div class="filter-field"><label for="subject-filter">Editorial subject</label><select id="subject-filter"><option value="">All subjects</option>{options(subjects)}</select></div><div class="filter-field"><label for="type-filter">Resource type</label><select id="type-filter"><option value="">All types</option>{options(sorted({r["type"] for r in RECORDS}))}</select></div><div class="filter-field"><label for="programme-filter">Research programme</label><select id="programme-filter"><option value="">All programmes</option>{''.join(f'<option value="{E(programme_id(p))}">{E(p["title"])}</option>' for p in PROGRAMMES)}</select></div><button class="reset" id="reset-filters">Clear filters</button><p class="filter-note">A selected catalogue, not the complete institutional holdings.<br><br>Publication dates and first editions are distinguished on item pages.</p></aside><section aria-label="Catalogue results"><div class="searchbar">{SEARCH_ICON}<label class="sr-only" for="catalogue-search">Search the catalogue</label><input id="catalogue-search" type="search" placeholder="Search titles, subjects, identifiers…" autocomplete="off"></div><div class="result-toolbar"><span id="result-count" aria-live="polite">{len(RECORDS)} records</span><div><label for="sort">Sort: </label><select id="sort"><option value="newest">Latest source publication</option><option value="oldest">Earliest source publication</option><option value="title">Title A–Z</option></select></div></div><div class="catalogue-grid" id="catalogue-grid">'''+''.join(card(r,search=True) for r in sorted(RECORDS,key=lambda r:r['date'],reverse=True))+'''</div><div id="no-results" class="empty" hidden><h2>No matching records</h2><p>Try a shorter search or clear the filters.</p></div></section></div>'''
write('catalogue.html',layout('Catalogue','Search Museum of One publications by title, subject, creator and persistent identifier.',catalogue,'catalogue.html',active='catalogue'))
collections=pagehead('Collections','Lines of inquiry.','Three editorial paths through the selected catalogue. These local groupings aid discovery; they are not claimed as original Zenodo collections.')
for group,(n,title,desc) in GROUPS.items():
 rs=[r for r in RECORDS if r['collection']==group]
 collections+=f'<section class="collection-block"><span class="collection-no">{n}</span><div><div class="eyebrow">{E(group)}</div><h2>{E(title)}</h2><p>{E(desc)}</p><p>{len(rs)} catalogue records</p><a class="text-link" href="catalogue.html?collection={urllib.parse.quote(group)}">Explore this collection ↗</a></div><div class="book-grid">'+''.join(card(r) for r in rs[:2])+'</div></section>'
collections+='<div style="height:50px"></div>'
write('collections.html',layout('Collections','Explore books, theoretical writings and field essays in Museum of One’s archival catalogue.',collections,'collections.html',active='collections'))

for r in RECORDS:
 rid=r['id'];base='../'; itemurl=url(f'items/{rid}.html'); doiurl='https://doi.org/'+r['doi']
 model=build_citation_model(r,catalogue_url=itemurl,pdf_url=url(f'items/{rid}.pdf') if r.get('reading_copy') else None)
 citation=visible_citation(model)
 institutional=r.get('institutional_url','https://www.museumofone.art/publications/')
 schema=build_graph(r,itemurl,ORIGIN)
 lic=r.get('license') or {}
 if isinstance(lic,str):lic={'label':lic}
 content=f'<div class="page-head"><div class="breadcrumb"><a href="../index.html">Library</a> / <a href="../catalogue.html">Catalogue</a> / {E(r["accession"])}</div></div><section class="item-head"><div><div class="eyebrow">{E(r["type"])} / {E(r["accession"])}</div><h1>{E(r["title"])}</h1><p class="item-author">{E(r["author"])}</p><p><span class="pill">{E(r["date"][:4])}</span><span class="pill">{E(r.get("version") or "Deposited edition")}</span><span class="pill">Source-linked record</span></p><p class="item-summary">{E(r["summary"])}</p><span class="source-label">Editorial catalogue summary · Based on linked sources</span><div class="actions"><a class="button" href="{E(r["zenodo_url"])}">Read the deposited work ↗</a><a class="text-link" href="#bibliographic-record">Explore the record ↓</a></div></div><div><div class="cover-well">{cover(r,base)}</div><div class="hero-caption"><span>{"PUBLICATION COVER" if r.get("cover") else "TYPOGRAPHIC CATALOGUE DISPLAY"}</span></div></div></section>'
 def field(label,value,note=''):
  if not value:return ''
  return f'<div><dt>{E(label)}</dt><dd>{value}'+(f'<span class="value-note">{E(note)}</span>' if note else '')+'</dd></div>'
 meta=field('Item number',E(r['accession']),'Local identifier; not an institutional accession number.')+field('Repository title',E(r.get('source_title') or r['title']),'As recorded in the deposited Zenodo edition.')
 meta+=field('Authorship',E(r['author']),'Corroborated against the institutional work record.')
 creators=r.get('creators',[])
 creators_text='; '.join((c if isinstance(c,str) else c.get('name','')+(f' [{c["role"]}]' if c.get('role') else '')) for c in creators)
 meta+=field('Repository creators',E(creators_text),'Source roles retained; these may differ from bibliographic authorship.')
 meta+=field('Zenodo publication date',E(r['date']),'Date of this repository edition; not necessarily the first edition.')
 if r.get('first_edition'):meta+=field('First-edition statement',E(r['first_edition']),'From Museum of One; distinct from the repository release.')
 meta+=field('Level of description',E(r.get('record_level','Item')))+field('Medium',E(r.get('medium')),'Digital medium derived from source file formats; not a claim about physical materials.')+field('Digital format',E('; '.join(r.get('digital_formats',[]))))+field('Extent',E(r.get('extent')))+field('Edition statement',E(r.get('edition_statement') or r.get('institutional_metadata',{}).get('edition')),'Institutional edition context; distinct from repository version.')
 meta+=field('Version',E(r.get('version') or 'Not supplied'))+field('Resource type',E(r['type']))+field('Publisher / imprint',E(r.get('publisher') or 'Museum of One'),'Institutional publication context; Zenodo is the repository.')
 meta+=field('DOI',f'<a href="{E(doiurl)}">{E(r["doi"])}</a>','Persistent identifier of this repository edition.')
 if r.get('conceptdoi'):meta+=field('Version-family DOI',f'<a href="https://doi.org/{E(r["conceptdoi"])}">{E(r["conceptdoi"])}</a>','Concept DOI groups versions. Cite the edition DOI for this record.')
 meta+=field('ISBN',E(r.get('isbn')),'Title-level identifier from linked sources; consult the edition statement for format applicability.')
 meta+=field('Language',E(r.get('language') or 'Not supplied'))
 if r.get('orcid'):meta+=field('Creator identifier',f'<a href="https://orcid.org/{E(r["orcid"].replace("https://orcid.org/",""))}">ORCID {E(r["orcid"].replace("https://orcid.org/",""))} ↗</a>')
 meta+=field('Record status',E(r.get('record_status')))
 meta+=field('Source review',TODAY,'Static source snapshot; no live repository synchronization.')
 body=repository_description_html(r)+f'<section class="item-section" id="bibliographic-record"><h2>Bibliographic record</h2><dl class="metadata">{meta}</dl></section>'
 body+='<section class="item-section" id="research-context"><h2>Research context</h2>'
 if programmes_for(r):
  body+='<p>Programme relationships follow the badges and research context on the corresponding Museum of One page.</p>'+programme_badges(r,base)
  for prog in programmes_for(r):
   body+=f'<p><strong>{E(prog["title"])}</strong><br>{E(prog.get("relation_label") or prog.get("relation") or "Related research")}. <a href="{E(prog["url"])}">View programme on Museum of One ↗</a></p>'
 else:body+='<p>No work-specific programme badge was verified for this item in the reviewed source. Explore the institutional directory for the wider research context.</p>'
 body+='<div class="institution-links"><a href="https://www.museumofone.art/research-programmes/">Research programmes ↗</a><a href="https://www.museumofone.art/publications/">Publication register ↗</a><a href="https://www.museumofone.art/the-journal-of-post-interpretive-criticism/">The Journal ↗</a></div></section>'
 body+='<section class="item-section"><h2>Subjects & discovery</h2><span class="source-label">Editorial subjects · Local discovery vocabulary</span>'+''.join(f'<a class="pill" href="../catalogue.html?subject={urllib.parse.quote(s)}">{E(s)}</a>' for s in r['subjects'])
 if r.get('keywords'):body+='<h3>Repository keywords</h3><p>'+E(' · '.join(r['keywords']))+'</p>'
 body+='</section>'
 body+=f'<section class="item-section" id="source-evidence"><h2>Source corroboration</h2><p>{E(r.get("corroboration") or "The deposited record is linked to the corresponding Museum of One work page. The catalogue retains edition-specific repository identifiers and institutional publication context separately.")}</p><ul class="source-list"><li><a href="{E(r["zenodo_url"])}">Zenodo edition record ↗</a><small>Deposited metadata, files, version and rights.</small></li><li><a href="{E(institutional)}">Museum of One work record ↗</a><small>Institutional title, authorship and publication context.</small></li></ul>'
 auth_data=json.loads((DATA/'authorities.json').read_text()) if (DATA/'authorities.json').exists() else {}
 matches=[w for w in auth_data.get('works',[]) if w['match_title'].lower() in (r['title']+' '+r.get('short_title','')).lower()]
 for w in matches:
  body+='<h3>External bibliographic context</h3><ul class="source-list">'
  for link in w.get('records',[]):
   body+=f'<li><a href="{E(link["url"])}">{E(link["title"])} ↗</a><small>{E(link.get("evidence") or link.get("note") or "Consult the external record for edition details.")}</small><small>Source status: {E(link.get("status", "not specified").replace("_", " "))}</small></li>'
  body+='</ul>'
 institution_meta=r.get('institutional_metadata',{})
 if institution_meta:
  body+='<h3>Institutional web record</h3><dl class="metadata">'+field('Web-page title',E(institution_meta.get('title')))+field('Web publication',E(institution_meta.get('web_publication')),'Date of the website article, distinct from the deposited work.')+field('Web record updated',E(institution_meta.get('web_updated')))+field('Publication status',E(institution_meta.get('publication_status')))+'</dl>'
 if r.get('discrepancies'):body+='<div class="note-box"><h3>Record notes</h3>'+''.join(f'<p>{E(x)}</p>' for x in r['discrepancies'])+'</div>'
 body+='</section>'
 body+='<section class="item-section" id="files-record"><h2>Files & preservation metadata</h2><p>File details and checksums are transcribed from Zenodo. This catalogue has not independently recomputed the checksums or made a separate preservation deposit.</p>'
 for f in r.get('files',[]):
  body+=f'<div class="file-record"><a href="{E(f.get("url"))}">{E(f.get("name"))} ↗</a><p>{E(f.get("size_label") or str(f.get("size", ""))+" bytes")}</p>'
  if f.get('checksum'):body+=f'<code>{E(f["checksum"])}</code>'
  body+='</div>'
 if r.get('osf_copy'):
  o=r['osf_copy']
  body+=f'<div class="file-record"><a href="{E(o["osf_url"])}">OSF · Exact edition PDF ↗</a><p>Byte-identical access copy of this DOI edition · {E(o["bytes"])} bytes · Verified {E(o["verified_at"])}.</p><code>SHA-256: {E(o["sha256"])}</code></div>'
 body+='<dl class="metadata">'+field('Repository record created',E(r.get('source_created')))+field('Repository metadata modified',E(r.get('source_modified')),'This timestamp describes the repository record, not necessarily a change to the work.')+'</dl>'
 rels=r.get('related_identifiers',[])
 if rels:
  body+='<details><summary>Source-declared bibliographic relationships</summary><ul class="source-list">'
  for rel in rels:
   identifier=rel.get('identifier','');target=('https://doi.org/'+identifier if rel.get('scheme')=='doi' else identifier)
   if target.startswith(('https://','http://')):body+=f'<li><a href="{E(target)}">{E(identifier)} ↗</a><small>Repository relation: {E(rel.get("relation"))}</small></li>'
   else:body+=f'<li>{E(identifier)}<small>Repository relation: {E(rel.get("relation"))}</small></li>'
  body+='</ul></details>'
 body+='</section>'
 body+='<section class="item-section" id="rights"><h2>Rights & access</h2><p>'+E(lic.get('label') or 'Consult the deposited record for the applicable licence.')+'</p>'
 if lic.get('url'):body+=f'<p><a href="{E(lic["url"])}">Read the source licence ↗</a></p>'
 if r.get('rights'):body+='<p>'+E(r['rights'])+'</p>'
 body+='<p>Public access does not establish unrestricted reuse. Consult the licence and notices attached to the specific file. Artwork reproduced within a text or on its cover may carry separate rights.</p></section>'
 body+=f'<section class="item-section"><h2>Cite this edition</h2><div class="citation" id="citation-text">{E(citation)}</div><button class="copy" data-copy="citation-text">Copy citation</button></section>'
 related=[x for x in RECORDS if x['id']!=rid and x['collection']==r['collection']][:3]
 if related:body+='<section class="item-section"><h2>Related reading</h2><ul class="source-list">'+''.join(f'<li><a href="{x["id"]}.html">{E(x["title"])} ↗</a></li>' for x in related)+'</ul><p>Editorial suggestions from this catalogue, not asserted bibliographic relationships.</p></section>'
 aside=f'<div class="access-card"><h2>Read & retrieve</h2><p>The published files remain with the repository.</p><a class="button" href="{E(r["zenodo_url"])}">Open Zenodo record ↗</a><a class="button outline" href="{E(doiurl)}">Resolve edition DOI ↗</a>'
 for f in r.get('files',[])[:4]:
  if f.get('url'):aside+=f'<p><a href="{E(f["url"])}">{E(f.get("name") or "Repository file")} ↗</a>'+ (f'<br>{E(f.get("size_label", ""))}' if f.get('size_label') else '')+'</p>'
 if r.get('osf_copy'):aside+=f'<p><a href="{E(r["osf_copy"]["osf_url"])}">OSF · Exact edition PDF ↗</a></p>'
 aside+='</div><div class="access-card"><h2>Record downloads</h2><p>Source-qualified metadata for research and reuse.</p>'
 for ext,label in [('json','Catalogue metadata · JSON'),('jsonld','Structured data · JSON-LD'),('xml','Qualified Dublin Core · XML'),('bib','Citation · BibTeX'),('ris','Citation · RIS'),('csl.json','Citation · CSL-JSON')]:aside+=f'<p><a href="../metadata/{rid}.{ext}" download>{label} ↓</a></p>'
 aside+=f'<p><a href="../metadata/source/{rid}.json" download>Original Zenodo metadata snapshot ↓</a></p></div><div class="access-card"><h2>Wider discovery</h2><p>Authority identifiers and external catalogue context are documented separately.</p><a class="text-link" href="../sources.html">Catalogue & authority links ↗</a></div>'
 content+='<nav class="record-tabs" aria-label="On this record"><a href="#bibliographic-record">Bibliographic record ↓</a><a href="#research-context">Research context ↓</a><a href="#source-evidence">Source evidence ↓</a><a href="#files-record">Files & preservation metadata ↓</a></nav>'
 content+=f'<div class="item-layout"><div>{body}</div><aside>{aside}</aside></div>'
 # Scholarly citation tags complement schema.org metadata.
 html=layout(r['title'],r['summary'],content,f'items/{rid}.html',base,schema=schema)
 if r.get('reading_copy'):
  shutil.copy2(OUT/'assets/documents'/f'{rid}.pdf',OUT/'items'/f'{rid}.pdf')
 if r.get('cover'):
  image=url(r['cover'])
  html=html.replace('</head>',f'<meta property="og:image" content="{E(image)}"><meta property="og:image:alt" content="{E(r.get("cover_alt") or "Publication cover of "+r["title"])}"><meta name="twitter:image" content="{E(image)}"></head>')
 tags=''.join(f'<meta name="{E(name)}" content="{E(value)}">' for name,value in scholar_meta(model))
 html=html.replace('</head>',tags+'</head>');write(f'items/{rid}.html',html)
 write(f'metadata/{rid}.json',json.dumps({**r,'field_assertions':build_assertions(r)},ensure_ascii=False,indent=2));write(f'metadata/{rid}.jsonld',json.dumps(schema,ensure_ascii=False,indent=2))
 write(f'metadata/{rid}.xml',build_dc(r))
 write(f'metadata/{rid}.bib',bibtex(model))
 write(f'metadata/{rid}.ris',ris(model))
 write(f'metadata/{rid}.csl.json',json.dumps(csl_json(model),ensure_ascii=False,indent=2))
 source=DATA/'source'/f'{rid}.json'
 if source.exists():shutil.copy2(source,OUT/'metadata/source'/f'{rid}.json')

about=pagehead('About the archive','Custody, context,<br>and careful description.'.replace('<br>',' '),'A digital reading room for Museum of One’s published work, rebuilt from public sources.')
about+='''<div class="reading"><h2>The scope of this catalogue</h2><p>This first edition gathers a selected corpus of publications associated with Museum of One and Dorian Vale. It is a new, source-linked catalogue, not an export of the previous catalogue or a claim to have recovered all its records.</p><p>The archive presents item records, publication covers, and an in-site document reader. Zenodo remains the source of record. Byte-identical local access copies support page turning, facing-page reading, thumbnails and zoom. Source checksums are matched before a reading copy is made available.</p><h2>How the records are made</h2><p>Zenodo supplies repository titles, dates, version identifiers, creators, file information, licence notices, and persistent identifiers. Museum of One’s corresponding work pages supply corroborating publication context. Where a page points to a different edition, that relationship is noted rather than treated as an exact match.</p><p>Each item separates repository publication dates from any first-edition statement. A local catalogue identifier is assigned for navigation; it is not represented as an accession number from the former archive.</p><h2>Editorial enrichment</h2><p>Concise catalogue summaries and local subject groupings are editorial additions based on the linked source material. They aid discovery without overwriting the original metadata. They are not publisher-approved abstracts or formally assigned Library of Congress subject headings.</p><p>Where Zenodo creator roles differ from the authorship stated on Museum of One, both are recorded. Version-specific DOIs are used for citations; concept DOIs are identified separately when available.</p><h2>Authority control & external links</h2><p>Identifiers and external links are qualified by what the source actually establishes. A catalogue search link is not evidence of a holding. A web-archive capture is not a book deposit. An ISBN or ISSN identifies a publication or serial; it does not establish peer review or institutional endorsement.</p><p><a href="sources.html">Read the sources and authority notes ↗</a></p><h2>Metadata for reuse</h2><p>Item records are available as JSON, schema.org JSON-LD, qualified Dublin Core XML, and BibTeX. Original Zenodo snapshots are retained separately. This provides portable descriptive metadata; the site does not claim formal archival standards certification or an OAI-PMH endpoint.</p><h2>Rights & corrections</h2><p>Licences are attached to individual works and editions. Cover illustrations and quoted artworks may retain separate rights. Consult the original deposited file before reusing material.</p><p>For institutional bibliographic corrections, contact <a href="mailto:research@museumofone.art">research@museumofone.art</a> and include the work’s DOI and the field in question.</p><h2>A portable archive</h2><p>This static site needs no subscription or database. Its HTML, metadata, and assets can be hosted on GitHub Pages. It is a custom catalogue rather than an installation of CollectionBuilder or Wax. Source review is a dated snapshot, not automatic synchronization with a Zenodo account.</p></div>'''
write('about.html',layout('About & metadata policy','The scope, source policy and editorial metadata practices of Museum of One’s archival catalogue.',about,'about.html',active='about'))

sourcepage=pagehead('Sources & authority records','Follow the evidence.','Repository records, institutional context, and external identifiers—each linked according to what it establishes.')
sourcepage+='''<div class="reading"><h2>Publication sources</h2><p><a href="https://www.museumofone.art/publications/">Museum of One publication register ↗</a> provides institutional work and edition records. Each catalogue item links to its corresponding page and the selected Zenodo edition. Original repository metadata is available from the item’s download panel.</p><h2>Library and Archives Canada</h2><p><a href="https://library-archives.canada.ca/eng">Library and Archives Canada ↗</a> provides national library, archival, and publication infrastructure. This catalogue does not assert that every included edition has a verified LAC holding.</p><p><a href="https://webarchiveweb.wayback.bac-lac.canada.ca/web/*/https://www.museumofone.art">Search LAC web-archive captures of Museum of One ↗</a>. This is a web-capture lookup, not evidence of a deposited book or a verified capture for a particular date.</p><h2>Identity and serial authority</h2><ul class="source-list"><li><a href="https://orcid.org/0009-0004-7737-5094">Dorian Vale · ORCID 0009-0004-7737-5094 ↗</a><small>Public ORCID profile inspected on 4 November 2026: its credit name and Museum of One link match. This does not verify affiliations or other biographical claims.</small></li><li><a href="https://portal.issn.org/resource/ISSN/2819-7232">ISSN Portal · 2819-7232 ↗</a><small>Key title: Post-interpretive criticism. Serial identity is distinct from the individual volume or edition.</small></li></ul><h2>Additional catalogue context</h2>'''
authfile=DATA/'authorities.json'
if authfile.exists():
 auth=json.loads(authfile.read_text())
 for entry in (auth if isinstance(auth,list) else auth.get('links',[])):
  if not entry.get('url'):continue
  sourcepage+=f'<p><a href="{E(entry["url"])}">{E(entry.get("title") or entry.get("label") or entry["url"])} ↗</a><br>{E(entry.get("scope") or entry.get("note") or entry.get("evidence") or "External reference; consult its source record.")}</p>'
sourcepage+='''<p>Unverified OCLC and ISNI claims are not promoted to confirmed catalogue identifiers. Where a record cannot be independently checked, follow the institutional source and inspect the identifier before relying on it.</p><h2>What “source-linked” means</h2><p>Corroboration connects the institutional description of a work with its public repository record. It does not independently validate the work’s research claims, certify peer review, or imply endorsement by a library or repository.</p><p>Original repository fields, institution-supplied information, and editorial additions are distinguished on item pages and in the downloadable JSON.</p></div>'''
write('sources.html',layout('Sources & authority records','Museum of One source records, Library and Archives Canada links, ORCID and ISSN authority context.',sourcepage,'sources.html'))
programme_content=pagehead('Research programmes','From inquiry to record.','Explore Museum of One’s research pathways and the published works linked to them. Programme relationships are transcribed from institutional work pages.')
programme_content+='<div class="institution-links"><a href="https://www.museumofone.art/research-programmes/">Open institutional programme directory ↗</a><a href="https://www.museumofone.art/research-record-2026/">Research Record 2026 ↗</a><a href="https://www.museumofone.art/research-working-papers/">Working paper series ↗</a></div>'
for p in PROGRAMMES:
 related=[r for r in RECORDS if any(x['url']==p['url'] for x in programmes_for(r))]
 programme_content+=f'<section class="programme-section" id="{E(programme_id(p))}"><div class="eyebrow">{E(p.get("status", "See institutional source"))}</div><h2>{E(p["title"])}</h2><p>{E(p.get("description") or "Programme details, current questions, and developments are maintained on Museum of One. This library presents the selected publications explicitly linked to that inquiry.")}</p><a class="text-link" href="{E(p["url"])}">Explore the programme on Museum of One ↗</a>'
 if related:
  programme_content+='<span class="source-label">Linked records in this selected catalogue</span><div class="programme-outputs">'
  for r in related:
   rel=next(x for x in programmes_for(r) if x['url']==p['url'])
   programme_content+=f'<a class="programme-output" href="items/{r["id"]}.html"><span class="catalogue-id">{E(r["accession"])} / {E(r["type"])}</span><h3>{E(r.get("short_title") or r["title"])}</h3><p>{E(rel.get("relation_label") or rel.get("relation"))}</p></a>'
  programme_content+='</div>'
 else:programme_content+='<p>No linked output has been included in this selected catalogue. Consult the programme page for its current record.</p>'
 programme_content+='</section>'
write('programmes.html',layout('Research programmes','Follow Museum of One research programme badges to source-linked publication records and ongoing inquiries.',programme_content,'programmes.html',active='programmes'))
subject_content=pagehead('Subject index','An index of ideas.','Browse the local editorial discovery vocabulary. Original repository keywords are retained separately on each item page.')+'<div class="directory-grid">'
for subject in sorted({s for r in RECORDS for s in r['subjects']}):
 count=sum(subject in r['subjects'] for r in RECORDS)
 subject_content+=f'<div class="directory-entry"><a href="catalogue.html?subject={urllib.parse.quote(subject)}">{E(subject)} ↗</a><p>{count:02d} CATALOGUE RECORDS</p></div>'
subject_content+='</div>'
subject_content=subject_content.replace('<div class="directory-grid">','<p class="vocabulary-register-link"><a href="vocabulary.html">Open the controlled vocabulary: preferred terms, definitions and synonyms ↗</a></p><div class="directory-grid">')
write('subjects.html',layout('Subject index','Browse editorial subjects across Museum of One books, treatises and critical research.',subject_content,'subjects.html'))
write('metadata/osf-editions.json',json.dumps([r['osf_copy'] for r in RECORDS if r.get('osf_copy')],ensure_ascii=False,indent=2))
write('metadata/catalogue.json',json.dumps({'title':'Museum of One Digital Archive Library','canonical_origin':ORIGIN,'reviewed':TODAY,'scope':'Selected corpus; not a complete recovery of the previous catalogue','records':[{**r,'field_assertions':build_assertions(r)} for r in RECORDS]},ensure_ascii=False,indent=2))
write('assets/favicon.svg','<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" fill="#f3f0e8"/><circle cx="32" cy="32" r="27" fill="none" stroke="#713e3e"/><text x="32" y="44" text-anchor="middle" font-family="Georgia,serif" font-size="36" fill="#713e3e">M</text></svg>')
build_finding_aid(RECORDS,PROGRAMMES,write,layout)
paths=['finding-aid.html','index.html','catalogue.html','collections.html','about.html','sources.html','programmes.html','subjects.html']+[f'items/{r["id"]}.html' for r in RECORDS]
paths+=build_reader_pages(RECORDS,write,layout,ORIGIN)
paths+=build_entity_pages(RECORDS,ENTITIES,write,layout,ORIGIN)
paths+=build_content_pages(RECORDS,CONTENTS,write,layout,ORIGIN)
paths+=build_vocabulary_pages(RECORDS,VOCABULARY,write,layout,ORIGIN)
paths+=build_policy_pages(RECORDS,write,layout,ORIGIN)
paths+=build_stewardship_page(RECORDS,write,layout,ORIGIN)
paths+=build_pirr_pages(RECORDS,PROGRAMMES,PIRR,write,layout,ORIGIN)
write('metadata/entities.json',json.dumps(ENTITIES,ensure_ascii=False,indent=2))
write('metadata/contents.json',json.dumps(CONTENTS,ensure_ascii=False,indent=2))
# One generated discovery model serves archive pages and the native Ghost entrance.
SYNC_WORK=Path(os.environ.get('WEBSITE_SYNC_DIR') or ROOT/'.sync-work')
from website_pages import build_website_pages
paths+=build_website_pages(SYNC_WORK,OUT,write,layout,ORIGIN)
GHOST_DISCOVERY=json.loads((SYNC_WORK/'public/discovery.json').read_text())['records'] if (SYNC_WORK/'public/discovery.json').exists() else []
DISCOVERY_V2=build_research_discovery(RECORDS,ENTITIES,VOCABULARY,PROGRAMMES,ORIGIN,root=ROOT,ghost_records=GHOST_DISCOVERY)
PASSAGES_V2=build_fulltext_index(RECORDS,ROOT,ORIGIN)
write('metadata/research-discovery.v2.json',encode_index(DISCOVERY_V2))
write('metadata/research-passages.v2.json',encode_index(PASSAGES_V2))
paths+=build_discovery_page(write,layout,DISCOVERY_V2,ORIGIN)
# Ghost consumes this partial from the exact same renderer as the homepage.
from explorer import render_explorer
write('integration/archive-explorer.hbs',render_explorer(RECORDS,PROGRAMMES,ORIGIN))
write('metadata/metadata-profile.json',json.dumps(PROFILE,ensure_ascii=False,indent=2))
write('metadata/relations.json',json.dumps(relation_register(ORIGIN),ensure_ascii=False,indent=2))
write('metadata/relationships.json',json.dumps({'profile_version':PROFILE['version'],'assertions':[a for r in RECORDS for a in r['relationship_assertions']]+typed_entity_relationship_assertions(ENTITIES,ORIGIN)},ensure_ascii=False,indent=2))
ALL_GRAPHS=collect_graphs(OUT,paths)
QUALITY=build_quality_report(RECORDS,ALL_GRAPHS,entity_graph(ENTITIES,ORIGIN),ORIGIN,output_dir=OUT,entity_records=ENTITIES)
write('metadata/quality-report.json',json.dumps(QUALITY,ensure_ascii=False,indent=2))
require_valid_report(QUALITY)
write('metadata/knowledge-graph.jsonld',json.dumps(combine_graphs(ALL_GRAPHS),ensure_ascii=False,indent=2))
paths+=build_quality_page(write,layout,QUALITY)
# Only dated local description events justify a sitemap modification date.
modified={f'items/{r["id"]}.html':r.get('record_modified') for r in RECORDS}
write('sitemap.xml','<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+''.join(f'<url><loc>{E(url(p))}</loc>'+ (f'<lastmod>{E(modified[p])}</lastmod>' if modified.get(p) else '')+'</url>' for p in paths)+'</urlset>')
write('robots.txt','User-agent: *\nAllow: /\nSitemap: '+url('sitemap.xml')+'\n')

# GitHub Pages serves this file at arbitrary missing paths. Root-relative assets
# and navigation must therefore work without knowing the requested directory.
errorbase=urllib.parse.urlparse(ORIGIN).path.rstrip('/')+'/'
errorcontent=f'<section class="page-head"><div class="eyebrow">Digital Archive Library / 404</div><h1>Record not found.</h1><p>This address does not identify an available archive page. Search the catalogue by title, local item number or DOI.</p><div class="actions"><a class="button" href="{E(errorbase)}catalogue.html">Search the catalogue</a><a class="text-link" href="{E(errorbase)}finding-aid.html">Consult the finding aid</a></div></section>'
errorhtml=layout('Page not found','Search the Museum of One Digital Archive Library for a publication or archival description.',errorcontent,'404.html',errorbase,schema={'@context':'https://schema.org','@type':'WebPage','name':'Page not found','url':url('404.html')})
errorhtml=errorhtml.replace(f'<script defer src="{errorbase}assets/app.js"></script>','').replace('</head>','<meta name="robots" content="noindex,follow"></head>')
write('404.html',errorhtml)
print(f'Built {len(paths)} HTML pages and metadata for {len(RECORDS)} records in {OUT}')

write('metadata/discovery.json',json.dumps(discovery_payload(RECORDS),ensure_ascii=False))
write('metadata/search-index.v1.json',encode_search_index(build_search_index(RECORDS,ORIGIN,SOURCE_SNAPSHOTS)))

write('CNAME','archive.museumofone.art\n')
write('.nojekyll','')
