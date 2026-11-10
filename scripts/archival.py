"""A distinct registry identity for the source-linked digital archive.

This presentation records local descriptive arrangement; it does not create
institutional accession, physical custody, or archival certification claims.
"""
from html import escape
from hashlib import sha256
from pathlib import Path, PurePosixPath
from urllib.parse import quote, urlparse
import re
import os
from explorer import render_explorer


def e(value):
    return escape(str(value or ''), quote=True)


def _formats(record):
    formats = record.get('digital_formats') or []
    labels = {'application/pdf': 'PDF', 'text/csv': 'CSV', 'application/zip': 'ZIP',
              'image/jpeg': 'JPEG', 'image/png': 'PNG', 'audio/mpeg': 'MP3',
              'video/mp4': 'MP4', 'application/json': 'JSON'}
    return ' / '.join(labels.get(x, x) for x in formats) or 'Digital record'


def _row(label, value):
    return f'<div><dt>{e(label)}</dt><dd>{value}</dd></div>'


def _item_register(record, base):
    grouping = record.get('collection') or 'Selected catalogue'
    archive = 'Museum of One Digital Archive Library'
    source = record.get('zenodo_url') or ''
    licence = record.get('license') or {}
    if isinstance(licence, str):
        licence = {'label': licence}
    files = record.get('files') or []
    banner = f'''<section class="archive-item-register" aria-labelledby="archive-record-reference"><div class="register-heading"><div><span class="register-label">Item record / Local reference code</span><h2 id="archive-record-reference">{e(record['accession'])}</h2></div><span class="register-type">{e(record.get('type'))}<br><strong>{e(_formats(record))}</strong></span></div><nav class="record-hierarchy" aria-label="Record hierarchy"><a href="{base}index.html">Archive</a><span aria-hidden="true">/</span><a href="{base}catalogue.html?collection={quote(grouping)}">{e(grouping)}</a><span aria-hidden="true">/</span><span aria-current="page">{e(record['accession'])}</span></nav><dl class="register-facts">'''
    banner += _row('Description level', e(record.get('record_level') or 'Item'))
    banner += _row('Source publication date', e(record.get('date')))
    banner += _row('Medium / format', e((record.get('medium') or 'Digital material') + ' · ' + _formats(record)))
    banner += _row('Digital extent', e(record.get('extent') or f'{len(files)} source files') + (f'<br>{record["page_count"]} PDF file pages' if record.get('page_count') else ''))
    banner += '</dl><p class="register-qualification">Reference codes identify records in this catalogue. They do not reproduce the previous catalogue accession register.</p></section>'
    context = '''<section class="item-section archival-context" id="archival-context"><div class="section-no">Arrangement / Access / Description</div><h2>Archival context & access</h2><dl class="context-register">'''
    context += _row('Catalogue', e(archive))
    context += _row('Arrangement', e(grouping) + '<span class="context-note">Local editorial grouping within a selected catalogue. This is not asserted as an original fonds or repository collection.</span>')
    context += _row('Custodial context', '<a href="' + e(source) + '">Zenodo source record ↗</a><span class="context-note">Description assembled from the public repository and institutional work record. No transfer of physical custody is recorded.</span>')
    context += _row('Access conditions', 'Digital access to the published source.<span class="context-note">The work’s own rights and licence govern reuse; third-party material may have separate conditions.</span>')
    licence_value = e(licence.get('label') or 'Consult the deposited edition')
    if licence.get('url'):
        licence_value = f'<a href="{e(licence["url"])}">{licence_value} ↗</a>'
    context += _row('Source licence', licence_value)
    context += _row('Description sources', f'<a href="{e(record.get("institutional_url"))}">Institutional work record ↗</a> · <a href="{e(source)}">Repository metadata ↗</a>')
    context += _row('Record review', e(record.get('record_reviewed') or record.get('source_review')) + '<span class="context-note">Catalogue review date; distinct from publication, deposit, and metadata-modification dates.</span>')
    context += '</dl></section>'
    return banner, context


def archival_page(path, html, records, programmes):
    """Apply the registry presentation after experience.enhance_page."""
    base = '../' if '/' in path else ''
    lookup = {str(r['id']): r for r in records}
    html = html.replace('</head>', f'<link rel="stylesheet" href="{base}assets/archive-identity.css"></head>')
    html = html.replace('<body ', '<body class="archive-registry" ', 1)
    html = html.replace('<strong>Museum of One</strong><small>Digital Archive Library</small>', '<strong>Digital Archive Library</strong><small>Museum of One / Source-linked catalogue</small>')
    html = html.replace('Museum of One / Research, criticism & preservation ↗', 'Museum of One / Institutional website ↗')
    html = html.replace('A source-linked digital catalogue · Selected works', 'Archive registry / Item-level records')
    html = html.replace('<h2>Museum of One</h2><p>An archival reading room', '<h2>Digital Archive Library</h2><p>A source-linked archive')

    html=html.replace(f'<a href="{base}about.html">About the archive</a>',f'<a href="{base}finding-aid.html">Finding aid</a>')
    html=html.replace(f'<a href="{base}subjects.html">Subject index</a>',f'<a href="{base}finding-aid.html">Finding aid & inventory</a><a href="{base}subjects.html">Subject index</a>')
    def jacket(match):
        attrs, target = match.groups()
        rid = PurePosixPath(urlparse(target).path).stem
        r = lookup.get(rid)
        if not r:
            return match.group(0)
        return f'<article class="catalogue-card"{attrs}><div class="jacket-reference"><span>{e(r["accession"])}</span><small>ITEM / {e(_formats(r))}</small></div><a class="book-card" href="{e(target)}">'
    html = re.sub(r'<article class="catalogue-card"([^>]*)><a class="book-card" href="([^"]+)">', jacket, html)

    if path == 'index.html':
        explorer_script = Path(__file__).resolve().parents[1] / 'dist/assets/archive-explorer.js'
        version = sha256(explorer_script.read_bytes()).hexdigest()[:12]
        html = html.replace('</head>', f'<link rel="stylesheet" href="assets/archive-explorer.css"><script defer src="assets/research-discovery.js"></script><script defer src="assets/archive-explorer.js?v={version}"></script></head>')
        html = html.replace('<div class="archive-masthead">', render_explorer(records, programmes, os.environ.get('SITE_ORIGIN', 'https://archive.museumofone.art'), standalone=True) + '<div class="archive-masthead">', 1)
        html = html.replace('<h1>The record.<br><em>In context.</em></h1>', '<h2 class="archive-reading-title">Open a document.<br><em>Stay with its record.</em></h2>')
        html = html.replace('Digital Archive Library</span><span class="archive-masthead-aside">Museum of One / Catalogue edition 02', 'Digital reading room</span><span class="archive-masthead-aside">Publication files / Selected editions')
        html = html.replace('01 / The collected shelf', 'Item register / Selected publications').replace('<h2>Selected editions</h2>', '<h2>Selected item records</h2>')
        html = html.replace('<h2>Follow a line of inquiry</h2>', '<h2>Arrangement & discovery</h2>')
        html = html.replace('<h2>Stay with the inquiry.</h2>', '<h2>Related research context</h2>')
    elif path == 'catalogue.html':
        html = html.replace('<h1>The published record.</h1>', '<h1>Item register</h1>')
        html = html.replace('Browse a selected corpus of Museum of One publications. Search titles, creators, subjects, ISBNs, and DOIs.', 'Item-level descriptions of a selected published corpus. Search reference codes, titles, creators, subjects, and persistent identifiers.')
    elif path.startswith('items/'):
        r = lookup.get(PurePosixPath(path).stem)
        if r:
            banner, context = _item_register(r, base)
            html = html.replace('<section class="item-head">', banner + '<section class="item-head">', 1)
            html = html.replace('<section class="item-section" id="research-context">', context + '<section class="item-section" id="research-context">', 1)
            html = html.replace('<a href="#bibliographic-record">Bibliographic record ↓</a>', '<a href="#bibliographic-record">Identity statement ↓</a><a href="#archival-context">Arrangement & access ↓</a>', 1)
            html = html.replace('<h2>Bibliographic record</h2>', '<h2>Identity statement</h2>', 1)
            html = html.replace('Editorial catalogue summary · Based on linked sources', 'Scope & content / Editorial catalogue description')
    def read_action(match):
        rid=match.group(1);record=lookup.get(rid)
        if not record or not record.get('reading_copy'):return match.group(0)
        return f'<a class="read-record" href="{base}read/{rid}.html">Read · {record["page_count"]} pp. ↗</a>'+match.group(0)
    html=re.sub(r'<button type="button" class="save-record" data-save="([^"]+)"',read_action,html)
    return html
