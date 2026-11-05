"""One progressively enhanced archive explorer for the archive and Ghost.

HTML, public record projection and interactions are generated from the reviewed
catalogue; Ghost consumes the generated partial rather than a parallel design.
"""
from html import escape
from urllib.parse import quote
import json
import re
from pathlib import Path
from image_dimensions import attributes
from integration_search import searchable_text


def e(value):
    return escape(str(value or ''), quote=True).replace('{{', '&#123;&#123;').replace('}}', '&#125;&#125;')


def render_explorer(records, programmes, origin, *, standalone=False):
    origin=origin.rstrip('/')
    dest=lambda path: path if standalone else origin+'/'+path
    asset=lambda path: path if standalone else "{{asset 'archive/explorer/"+path.removeprefix('assets/')+"'}}"
    index='metadata/research-discovery.v2.json' if standalone else "{{asset 'archive/research-discovery.v2.json'}}"
    passages='metadata/research-passages.v2.json' if standalone else "{{asset 'archive/research-passages.v2.json'}}"
    groups=list(dict.fromkeys(r['collection'] for r in records))
    # The contextual register also includes people linked through exchanges/programmes.
    entities=len(json.loads((Path(__file__).resolve().parents[1]/'data/entities.json').read_text()))
    chapters=sum(len(r.get('contents',[])) for r in records)
    heading='h1' if standalone else 'h2'
    model=[]
    for r in records:
        row={k:r.get(k) for k in ['id','accession','title','short_title','author','date','date_precision','type','collection','summary','subjects','doi','conceptdoi','isbn','language','medium','digital_formats','extent','license','institutional_url','zenodo_url','research_programmes','edition_statement','first_edition']}
        row['id']=str(r['id']);model.append(row)
    def card(r):
        rid=str(r['id']);title=r.get('short_title') or r['title']
        image=(f'<img src="{asset(r["cover"])}" alt="{e(r.get("cover_alt") or "Published cover of "+r["title"])}" loading="lazy" decoding="async"{attributes(Path(__file__).resolve().parents[1]/"dist"/r["cover"])}>' if r.get('cover') else f'<div class="ax-type-cover"><span>Museum of One<br>Archival Library</span><strong>{e(title)}</strong><small>{e(r["author"])}</small></div>')
        search=searchable_text(r)
        read=f'<a data-ax-handoff href="{e(dest("read/"+rid+".html"))}">Read · {r["page_count"]} pp. ↗</a>' if r.get('reading_copy') else ''
        return f'''<article class="ax-card" data-ax-record="{rid}" data-search="{e(search)}" data-collection="{e(r['collection'])}" data-type="{e(r['type'])}" data-year="{e(r['date'][:4])}" data-title="{e(r['title'])}" data-date="{e(r['date'])}"><div class="ax-reference"><span>{e(r['accession'])}</span><span>Item / PDF</span></div><a class="ax-cover" data-ax-handoff href="{e(dest('items/'+rid+'.html'))}">{image}</a><div class="ax-card-copy"><p class="ax-label">{e(r['type'])} · {e(r['date'])}</p><h3><a data-ax-handoff href="{e(dest('items/'+rid+'.html'))}">{e(title)}</a></h3><p class="ax-card-author">{e(r['author'])}</p><p class="ax-card-summary">{e(r['summary'])}</p><div class="ax-card-actions">{read}<button type="button" data-ax-save="{rid}" aria-pressed="false" aria-label="Save {e(title)} to reading list">＋ Save</button></div></div></article>'''
    def nav(label,view,path,extra=''):
        return f'<a href="{e(dest(path))}" data-ax-view="{view}"{extra}>{label}</a>'
    html=f'''<section class="archive-explorer" id="archive-explorer" data-archive-explorer data-standalone="{str(standalone).lower()}" data-origin="{e(origin)}" aria-label="Interactive archive explorer">
<div class="ax-topline"><span>Archive registry / Item-level records</span><a data-ax-handoff href="{e(origin+'/')}">Open full archive ↗</a><button type="button" data-ax-expand aria-pressed="false" hidden>Expand explorer</button></div>
<div class="ax-workspace"><aside class="ax-tree" aria-label="Explorer collection tree"><details><summary>Browse the archive<small>{len(records)} items · {chapters} analytic parts</small></summary><nav aria-label="Explorer pathways"><a class="ax-tree-root" href="{e(dest('finding-aid.html'))}">Museum of One<br>Digital Archive Library</a>{nav('Overview','overview','index.html')}{nav('Item register <small>'+str(len(records))+'</small>','catalogue','catalogue.html')}'''
    for group in groups:
        rs=[r for r in records if r['collection']==group]
        html+=f'<details class="ax-tree-group"><summary>{e(group)}<small>{len(rs):02d}</small></summary><a href="{e(dest("catalogue.html?collection="+quote(group)))}" data-ax-collection="{e(group)}">Browse this collection →</a><ul>'+''.join(f'<li><a data-ax-handoff href="{e(dest("items/"+str(r["id"])+".html"))}"><small>{e(r["accession"])}</small>{e(r.get("short_title") or r["title"])}</a></li>' for r in rs)+'</ul></details>'
    html+=nav('Discover across the archive','discover','research-discovery.html')+nav('Reading list <span data-ax-count>0</span>','reading','catalogue.html')
    for path,label in [('contents.html','Chapters & essays'),('people.html','People & organisations'),('artworks.html','Artworks discussed'),('programmes.html','Research pathways'),('vocabulary.html','Discovery vocabulary'),('metadata-quality.html','Catalogue quality'),('finding-aid.html','Finding aid')]:
        html+=f'<a href="{e(dest(path))}">{label} ↗</a>'
    html+='</nav><p class="ax-note">Published items and analytic parts. Editorial arrangement is described in the finding aid.</p></details></aside><div class="ax-workbench">'
    html+=f'''<div class="ax-opening"><p class="ax-label">Research catalogue / Museum of One</p><{heading} class="ax-title" id="ax-title">The archive,<br><em>in context.</em></{heading}><p>Read the publications. Follow ideas, artworks and people through a connected record of independent inquiry.</p><form class="ax-entry-search" data-ax-entry action="{e(dest('research-discovery.html'))}" method="get" role="search"><label for="ax-entry-query" class="ax-sr">Discover across the archive</label><input id="ax-entry-query" name="q" type="search" placeholder="A title, person, artwork or idea…"><button type="submit">Discover ↗</button></form><dl class="ax-totals">'''
    for label,count in [('Publications',len(records)),('Chapters & essays',chapters),('Contextual entities',entities),('Research pathways',len(programmes))]:html+=f'<div><dt>{e(label)}</dt><dd>{count:02d}</dd></div>'
    html+='</dl></div><nav class="ax-tabs" aria-label="Archive explorer views">'+''.join(nav(label,view,path) for label,view,path in [('Overview','overview','index.html'),('Catalogue','catalogue','catalogue.html'),('Discover','discover','research-discovery.html'),('Reading list','reading','catalogue.html')])+'</nav>'
    html+='<div data-ax-panel="overview"><div class="ax-section-head"><h3>The collection register</h3>'+nav('Browse publication records ↗','catalogue','catalogue.html')+'</div>'
    for i,group in enumerate(groups):
        rs=[r for r in records if r['collection']==group]
        html+=f'<a class="ax-collection-row" href="{e(dest("catalogue.html?collection="+quote(group)))}" data-ax-collection="{e(group)}"><span>{i+1:02d}</span><span><strong>{e(group)}</strong><small>Editorial arrangement / Item-level description</small></span><span>{len(rs):02d} described items ↗</span></a>'
    html+='<div class="ax-section-head"><h3>On the reading desk</h3>'+nav('View the complete shelf ↗','catalogue','catalogue.html')+'</div><div class="ax-grid ax-featured">'+''.join(card(r) for r in records[:4])+'</div></div>'
    def options(values):return ''.join(f'<option value="{e(v)}">{e(v)}</option>' for v in values)
    html+=f'''<section data-ax-panel="catalogue" aria-labelledby="ax-catalogue-heading" hidden><div class="ax-section-head"><h3 id="ax-catalogue-heading">The item register</h3></div><form data-ax-filter class="ax-filters" role="search" action="{e(dest('catalogue.html'))}" method="get"><label>Search the catalogue<input aria-label="Search the catalogue" name="q" type="search" placeholder="Title, creator, subject or DOI"></label><label>Collection<select aria-label="Collection" name="collection"><option value="">All collections</option>{options(groups)}</select></label><label>Publication year<select aria-label="Publication year" name="year"><option value="">All years</option>{options(sorted({r['date'][:4] for r in records},reverse=True))}</select></label><label>Material type<select aria-label="Material type" name="type"><option value="">All types</option>{options(sorted({r['type'] for r in records}))}</select></label><label>Sort<select aria-label="Sort" name="sort"><option value="reference">Reference order</option><option value="newest">Latest source publication</option><option value="oldest">Earliest source publication</option><option value="title">Title A–Z</option></select></label><button type="reset">Clear filters</button><button class="ax-fallback-submit" type="submit">Search</button></form><div class="ax-resultbar"><p data-ax-results role="status">{len(records)} records</p><div role="group" aria-label="Catalogue presentation"><button type="button" data-ax-layout="shelf" aria-pressed="true">Shelf</button><button type="button" data-ax-layout="list" aria-pressed="false">List</button></div></div><div class="ax-grid" data-ax-cards>'''+''.join(card(r) for r in records)+'''</div><p data-ax-empty hidden>No matching records. Try fewer words or clear the filters.</p></section>'''
    html+=f'''<section data-ax-panel="discover" hidden><div data-research-discovery data-archive-origin="{e(origin)}" data-index-snapshot="{index}" data-passages-url="{passages}" data-local-results="{str(standalone).lower()}"><div class="ax-section-head"><h3>Follow a line of inquiry</h3></div><form data-discovery-form class="ax-discovery-form" role="search" method="get" action="{e(dest('research-discovery.html'))}"><label for="ax-discovery-query">Search titles, names, identifiers and concepts</label><input id="ax-discovery-query" name="q" type="search" placeholder="A title, person, artwork or idea…"><div class="ax-discovery-controls"><label>Look in<select aria-label="Look in" name="kind"><option value="">All records</option><option value="publication">Publications</option><option value="chapter">Chapters & essays</option><option value="entity">People, artworks & events</option><option value="concept">Concepts & subjects</option><option value="programme">Research programmes</option><option value="website">Writing & website pages</option><option value="passage">Source passages only</option></select></label><label class="ax-check"><input type="checkbox" name="fulltext" value="1"> Also search passages in publications</label><button type="submit">Search</button></div></form><p data-discovery-status role="status" aria-live="polite">Search the archive or follow a collection link.</p><ol data-discovery-results class="ax-discovery-results"></ol><button type="button" data-discovery-more hidden>Show more results</button><p class="ax-note">Passages quote the original PDF text layer and link to its file page. Check the deposited PDF for layout, wording and rights.</p></div></section>'''
    html+='''<section data-ax-panel="reading" hidden><div class="ax-section-head"><h3>A shelf of your own.</h3><button type="button" data-ax-export>Export reading list · CSV ↓</button></div><p class="ax-note">Saved in this browser on this site. Opening an archive record carries your selected list to the archive; existing saved records there are retained.</p><div data-ax-reading></div><div class="ax-reading-actions"><button type="button" data-ax-compare disabled>Compare selected records</button><button type="button" data-ax-clear>Clear list</button></div><div data-ax-comparison></div></section><p class="ax-live" data-ax-message role="status" aria-live="polite"></p><noscript><p>Use the collection and publication links to browse the archive. Interactive filters and saved lists require JavaScript.</p></noscript></div></div>'''
    # JSON remains inert in HTML and in the generated Handlebars partial.
    raw=json.dumps(model,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c').replace('{{','\\u007b\\u007b')
    html+='<script type="application/json" data-ax-records>'+raw+'</script></section>'
    if standalone:
        html=re.sub(r'(\<div class="ax-section-head"\>)<h3([^>]*)>(.*?)</h3>',r'\1<h2\2>\3</h2>',html)
    return html
