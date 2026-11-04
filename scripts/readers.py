"""Reading-copy manifests and book-reader pages. Source PDFs remain byte-for-byte copies."""
from pathlib import Path
from html import escape
import json
E=lambda v:escape(str(v or ''),quote=True)

def apply_reading_metadata(records,root):
 path=root/'data/readers.json';manifests=json.loads(path.read_text()) if path.exists() else []
 by_id={r['id']:r for r in manifests}
 result=[]
 for record in records:
  r=dict(record);copy=by_id.get(r['id'])
  if copy:
   r['reading_copy']=copy;r['page_count']=copy['page_count']
   assertions=[a for a in r.get('field_assertions',[]) if a.get('field') not in ['reading_copy','page_count']]
   for field,value,note in [('reading_copy',copy,'Byte-identical local access copy. Source MD5 was recomputed and matched; SHA-256 and page count were measured from the downloaded PDF. This is not a preservation-deposit claim.'),('page_count',copy['page_count'],'Total PDF file pages measured from the deposited file, including cover and unnumbered pages. Not a claim about printed pagination.')]:
    assertions.append({'field':field,'value':value,'source_url':copy['source_url'],'status':'derived_file_inspection','reviewed':copy['verified_at'],'note':note})
   r['field_assertions']=assertions
  result.append(r)
 return result

def reader_link(path,html,records):
 if not path.startswith('items/'):return html
 r=next((r for r in records if r['id']==Path(path).stem),None)
 if not r or not r.get('reading_copy'):return html
 copy=r['reading_copy'];url='../read/'+r['id']+'.html'
 primary=f'<a class="button" href="{url}">Read in the archive <span aria-hidden="true">↗</span></a>'
 html=html.replace(f'<a class="button" href="{E(r["zenodo_url"])}">Read the deposited work ↗</a>',primary,1)
 panel=f'''<section class="item-reader-access" aria-labelledby="reading-copy-heading"><div><span class="register-label">Digital object / Reading copy</span><h2 id="reading-copy-heading">Open the document</h2><p>{copy['page_count']} PDF pages · Facing-page reader · Original deposited file</p></div><a class="button" href="{url}">Enter the document reader ↗</a></section>'''
 html=html.replace('<nav class="record-tabs"',panel+'<nav class="record-tabs"',1)
 html=html.replace('<h2>Read & retrieve</h2>','<h2>Read & retrieve</h2>'+f'<a class="button" href="{url}">Read in the archive ↗</a>',1)
 html=html.replace('This catalogue has not independently recomputed the checksums or made a separate preservation deposit.','The reading copy’s source MD5 was independently recomputed and matched. Its SHA-256 and PDF page count are recorded below. No separate preservation deposit is claimed.')
 # Two comparable measurements: file byte extent and PDF page count.
 html=html.replace('<dt>Digital format</dt>',f'<dt>PDF page extent</dt><dd>{copy["page_count"]} file pages, including covers and unnumbered pages</dd></div><div><dt>Digital format</dt>',1)
 details=f'''<div class="reading-copy-audit"><h3>Reading-copy verification</h3><dl class="metadata"><div><dt>Access-copy status</dt><dd>Byte-identical to the deposited PDF</dd></div><div><dt>Verified source checksum</dt><dd><code>{E(copy['checksum'])}</code></dd></div><div><dt>Access-copy SHA-256</dt><dd><code>{E(copy['sha256'])}</code></dd></div><div><dt>File pages</dt><dd>{copy['page_count']}</dd></div><div><dt>Verification date</dt><dd>{E(copy['verified_at'])}</dd></div></dl><p>The original repository file remains the source of record. The local copy provides reading access.</p></div>'''
 html=html.replace('<h2>Files & preservation metadata</h2>','<h2>Files & preservation metadata</h2>'+details,1)
 return html

def build_reader_pages(records,write,layout,origin):
 available=[r for r in records if r.get('reading_copy')]
 for r in available:
  copy=r['reading_copy'];rid=r['id'];title=r['short_title'];lic=r.get('license') or {}
  content=f'''<div class="reader-breadcrumb"><a href="../index.html">Archive</a> / <a href="../catalogue.html">Item register</a> / <a href="../items/{rid}.html">{E(r['accession'])}</a> / Reading copy</div>
<section class="reader-shell" id="book-reader" data-manifest="../metadata/readers/{rid}.json" aria-label="Publication reader"><header class="reader-header"><div><small class="reader-reference">{E(r['accession'])} / Digital reading copy</small><h1 id="reader-title">{E(title)}</h1></div><a class="reader-backlink" href="../items/{rid}.html">Return to item record ↗</a></header>
<nav class="reader-controls" id="reader-controls" aria-label="Document controls"><button type="button" id="reader-thumbs-toggle" aria-expanded="false" aria-controls="reader-thumbnails">Thumbnails</button><button type="button" id="reader-prev" aria-label="Previous page or spread">← Previous</button><label for="reader-page">Page <input id="reader-page" type="number" value="1" min="1" max="{copy['page_count']}" inputmode="numeric"> / <span id="reader-total">{copy['page_count']}</span></label><button type="button" id="reader-next" aria-label="Next page or spread">Next →</button><label for="reader-mode" class="sr-only">Page layout</label><select id="reader-mode"><option value="auto">Automatic layout</option><option value="single">Single page</option><option value="spread">Facing pages</option></select><button type="button" id="reader-zoom-out" aria-label="Zoom out">−</button><button type="button" id="reader-zoom-in" aria-label="Zoom in">＋</button><button type="button" id="reader-fit">Fit page</button><button type="button" id="reader-fullscreen" aria-pressed="false">Full screen</button><label class="sr-only" for="reader-progress">Move through the document</label><input type="range" id="reader-progress" value="1" min="1" max="{copy['page_count']}" aria-valuetext="Page 1 of {copy['page_count']}"></nav>
<div id="reader-loading" class="reader-loading">Opening the deposited document…</div><div class="reader-workspace"><aside id="reader-thumbnails" class="reader-thumbnails" aria-label="Page thumbnails" hidden><div id="reader-thumb-list" class="reader-thumb-list"></div></aside><div id="reader-stage" class="reader-stage" tabindex="0" aria-label="Book pages. Use left and right arrow keys to turn pages." aria-busy="true"><div id="reader-pages" class="reader-pages"></div></div></div><p id="reader-status" class="reader-status" role="status" aria-live="polite">Loading the reading copy.</p>
<div class="reader-downloads"><a id="reader-fallback" href="../assets/documents/{rid}.pdf">Open or download PDF ↗</a><a href="{E(r['zenodo_url'])}">Zenodo source record ↗</a><p>{E(lic.get('label'))}. Original file retained unchanged; third-party material may have separate rights.</p></div></section>
<noscript><p class="reader-help">The page-turning reader requires JavaScript. <a href="../assets/documents/{rid}.pdf">Open the complete PDF</a> to read it in your browser.</p></noscript><p class="reader-help">Use <kbd>←</kbd> and <kbd>→</kbd> inside the reader to turn pages. Page numbers refer to the PDF file, including covers. Open a page’s text disclosure to read its extracted text; extraction order can differ from the page layout.</p><div class="reader-object-record"><span class="register-label">Access copy / Source verification</span><dl><div><dt>Reference</dt><dd><a href="../items/{rid}.html">{E(r['accession'])}</a></dd></div><div><dt>Extent</dt><dd>{copy['page_count']} PDF pages · {copy['bytes']:,} bytes</dd></div><div><dt>Source checksum</dt><dd>{E(copy['checksum'])} · Matched {E(copy['verified_at'])}</dd></div><div><dt>Original filename</dt><dd>{E(copy['source_filename'])}</dd></div></dl><p>The local reading copy is not a replacement for the item’s version, citation, rights, or repository record. <a href="../items/{rid}.html">Inspect the complete archive item ↗</a></p></div><p class="reader-credits">Reader powered by <a href="https://mozilla.github.io/pdf.js/">Mozilla PDF.js</a> · <a href="../assets/vendor/pdfjs/LICENSE">Apache 2.0 licence</a>.</p>'''
  schema={'@context':'https://schema.org','@type':'WebPage','name':'Read '+r['title'],'url':origin+'/read/'+rid+'.html','about':{'@id':'https://doi.org/'+r['doi']},'isPartOf':{'@id':origin+'/#website'}}
  html=layout('Read '+title,'Read the deposited publication in the Museum of One Digital Archive Library.',content,'read/'+rid+'.html',base='../',schema=schema)
  html=html.replace('</head>','<link rel="stylesheet" href="../assets/book-reader.css"><script type="module" src="../assets/book-reader.js"></script></head>')
  write('read/'+rid+'.html',html)
  write('metadata/readers/'+rid+'.json',json.dumps(copy,ensure_ascii=False,indent=2))
 return ['read/'+r['id']+'.html' for r in available]
