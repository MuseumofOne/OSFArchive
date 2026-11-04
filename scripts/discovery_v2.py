"""Typed public discovery and verbatim PDF text-layer retrieval.

This is a derived access index, not a second descriptive catalogue. Publication
eligibility is checked against repository snapshots. Other types need an
explicit public, evidenced relationship to the reviewed catalogue/vocabulary.
"""
from collections import Counter
from hashlib import sha256
from html import escape
import json
from pathlib import Path
import re
from urllib.parse import urlsplit

from integration_search import load_source_snapshots, public_export_eligible, searchable_text
from identities import institutional_scope

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_VERSION = 2


def encode_index(payload):
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def _finish(records, origin, index_kind='discovery', **extra):
    ids = [r['id'] for r in records]
    if len(ids) != len(set(ids)):
        raise ValueError('Duplicate discovery identifier')
    payload = dict(schema_version=2, index_kind=index_kind, canonical_origin=origin,
                   scope='Selected public Museum of One research corpus; descriptive relationships retain their evidence.',
                   records=sorted(records, key=lambda r: r['id']), **extra)
    payload['content_version'] = sha256(encode_index(payload).encode()).hexdigest()
    return payload


def _origin(origin):
    value = str(origin).rstrip('/')
    u = urlsplit(value)
    if u.scheme != 'https' or not u.hostname or u.username or u.password or u.query or u.fragment:
        raise ValueError('Discovery origin must be an absolute HTTPS base')
    if any(part in ('.', '..') for part in u.path.split('/')):
        raise ValueError('Invalid discovery base path')
    return value


def _public(value):
    return not any(value.get(k) not in (None, False) for k in ('private', 'draft', 'is_draft', 'hidden')) and value.get('visibility') in (None, 'public') and all(value.get(k) in (None, True) for k in ('public', 'published', 'is_published'))


def _url(value):
    try:
        parsed = urlsplit(str(value or ''))
        if parsed.scheme == 'https' and parsed.hostname and not parsed.username and not parsed.password:
            return str(value)
    except ValueError:
        pass
    return ''


def _slug(value):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*', value):
        raise ValueError('Invalid discovery identifier: ' + str(value))
    return value


def _texts(values):
    return list(dict.fromkeys(str(v).strip() for v in values if v is not None and str(v).strip()))


def _eligible(records, root):
    sources = load_source_snapshots(records, Path(root) / 'data/source')
    invalid = [str(r.get('id')) for r in records if not public_export_eligible(r, sources.get(str(r.get('id'))))]
    if invalid:
        raise ValueError('Discovery contains records not eligible for public export: ' + ', '.join(invalid))
    return {str(r['id']): r for r in records}


def _source(url, label='', **extra):
    return {'url': _url(url), 'label': label, **extra}


def _edge(relation, target_id, url, source_url='', note='', **extra):
    return dict(relation=relation, target_id=target_id, url=url,
                source_url=_url(source_url), note=note, **extra)


def _record(id, kind, title, url, summary='', **extra):
    row = dict(id=id, kind=kind, title=title, url=url, summary=summary,
               aliases=[], identifiers=[], relationships=[], sources=[], **extra)
    return row


def build_research_discovery(records, entities, vocab, programmes, origin, *, root=ROOT, ghost_records=()):
    origin = _origin(origin)
    by_id = _eligible(records, root)
    public_entities = {e['id']: e for e in entities if _public(e) and e.get('sources') and any(str(link.get('record_id')) in by_id and _url(link.get('source_url')) for link in e.get('record_links', []))}
    terms = {t['id']: t for t in vocab.get('terms', []) if _public(t) and t.get('editorial_owner') and t.get('modified') and any(str(rid) in by_id for rid in t.get('provenance', {}).get('record_ids', []))}
    public_programmes = [p for p in programmes if _public(p) and _url(p.get('source_url')) and p.get('reviewed')]
    programme_urls = {p['url'] for p in public_programmes}
    programme_ids = {urlsplit(u).path.rstrip('/').split('/')[-1] for u in programme_urls}
    rows = []
    for rid, record in by_id.items():
        discovery_record = {**record,
                            'entity_links': [e for e in record.get('entity_links', []) if e['id'] in public_entities],
                            'controlled_subjects': [t for t in record.get('controlled_subjects', []) if t['id'] in terms],
                            'research_programmes': [p for p in record.get('research_programmes', []) if p.get('url') in programme_urls],
                            'pirr_references': [p for p in record.get('pirr_references', []) if p.get('programme_key') in programme_ids]}
        row = _record('publication:' + rid, 'publication', record['title'], origin + '/items/' + rid + '.html', record.get('summary', ''))
        row.update(identity='https://doi.org/' + record['doi'], date=record.get('date', ''),
                   author=record.get('author', ''), collection=record.get('collection', ''),
                   subjects=record.get('subjects', []), resource_type=record.get('type', ''),
                   aliases=_texts([record.get('short_title'), record.get('source_title')] + [a.get('title') for a in record.get('alternate_titles', [])]),
                   identifiers=_texts([rid, record.get('accession'), record.get('doi'), record.get('conceptdoi'), record.get('isbn')]),
                   sources=[_source(record['zenodo_url'], 'Repository edition', reviewed=record.get('source_review', ''))],
                   search_text=searchable_text(discovery_record))
        if record.get('osf_copy'):
            o = record['osf_copy']
            row['sources'].append(_source(o['osf_url'], 'OSF exact edition PDF', reviewed=o['verified_at']))
            row['identifiers'].append(o['osf_url'])
        row['identifier_scopes'] = {record['doi']: 'Deposited edition DOI'}
        if record.get('conceptdoi'):
            row['identifier_scopes'][record['conceptdoi']] = 'Concept DOI; groups repository versions'
        if record.get('isbn'):
            row['identifier_scopes'][record['isbn']] = 'Title-level ISBN; applicability to this deposited file is not established'
        for entity in discovery_record.get('entity_links', []):
            eid = _slug(entity['id'])
            row['relationships'].append(_edge(entity['relation'], 'entity:' + eid, origin + '/entities/' + eid + '.html', entity.get('source_url'), entity.get('note', ''), evidence_scope=entity.get('evidence_scope', 'work')))
            row['search_text'] += ' ' + ' '.join(entity.get('variants', []))
        for term in discovery_record.get('controlled_subjects', []):
            tid = _slug(term['id'])
            row['relationships'].append(_edge('editorial subject', 'concept:' + tid, origin + '/vocabulary.html#' + tid, record['zenodo_url'], 'Local access-term assignment; source wording is retained separately.'))
        for part in record.get('contents', []):
            cid = _slug(part['id'])
            start, end = part.get('pdf_start'), part.get('pdf_end')
            count = record.get('reading_copy', {}).get('page_count', record.get('page_count', 0))
            evidence = part.get('evidence', {})
            if not _public(part) or not isinstance(start, int) or not isinstance(end, int) or not 1 <= start <= end <= count or not evidence.get('reviewed'):
                raise ValueError('Component lacks public, checked pagination: ' + rid + '/' + cid)
            child_id = 'chapter:' + rid + ':' + cid
            child_url = origin + '/parts/' + rid + '-' + cid + '.html'
            reader = origin + '/read/' + rid + '.html#page=' + str(start)
            child = _record(child_id, 'chapter', part['title'], child_url,
                            part['type'] + ' in ' + record['title'] + '. Authorship and edition context inherited from the parent publication.')
            child.update(identity=child_url + '#component', parent_id=row['id'], parent_title=record['title'], author=record.get('author', ''), date=record.get('date', ''), collection=record.get('collection', ''),
                         identifiers=[part['reference']], reader_url=reader, pdf_start=start, pdf_end=end,
                         sources=[_source(origin + '/assets/documents/' + rid + '.pdf#page=' + str(start), 'Checked source PDF', reviewed=evidence['reviewed'], pdf_pages=[start, end], method=evidence.get('method', ''))],
                         relationships=[_edge('part of this edition', row['id'], row['url'], record['zenodo_url'])],
                         search_text=' '.join([part['title'], record['title'], record.get('author', ''), part['reference']]))
            row['relationships'].append(_edge('contains', child_id, child_url, child['sources'][0]['url'], 'Checked contents and pagination.'))
            rows.append(child)
        rows.append(row)

    for eid, entity in public_entities.items():
        eid = _slug(eid)
        row = _record('entity:' + eid, 'entity', entity['label'], origin + '/entities/' + eid + '.html', entity.get('summary', ''))
        row.update(identity=row['url'] + '#entity', entity_type=entity['type'], aliases=_texts(entity.get('variants', [])),
                   identifiers=_texts([i.get('value') for i in entity.get('identifiers', [])] + ['MOO-CTX-' + eid]),
                   sources=[_source(s['url'], s.get('label', ''), note=s.get('note', '')) for s in entity['sources'] if _url(s.get('url'))])
        for link in entity.get('record_links', []):
            rid = str(link['record_id'])
            if rid in by_id and _url(link.get('source_url')):
                row['relationships'].append(_edge(link['relation'], 'publication:' + rid, origin + '/items/' + rid + '.html', link['source_url'], link.get('note', ''), evidence_scope=link.get('evidence_scope', 'work')))
        for link in entity.get('relationships', []):
            if link['id'] in public_entities and _url(link.get('source_url')):
                row['relationships'].append(_edge(link['relation'], 'entity:' + link['id'], origin + '/entities/' + link['id'] + '.html', link['source_url'], link.get('note', '')))
        row['search_text'] = ' '.join(_texts([row['title'], row['summary'], entity['type']] + row['aliases'] + row['identifiers']))
        rows.append(row)

    for tid, term in terms.items():
        tid = _slug(tid)
        row = _record('concept:' + tid, 'concept', term['preferred_label'], origin + '/vocabulary.html#' + tid, term.get('definition', ''))
        row.update(identity=row['url'], concept_type=term['kind'], aliases=_texts(term.get('alternative_labels', [])), identifiers=[term['persistent_id']],
                   scope_note=term.get('scope_note', ''), sources=[_source(u, 'Vocabulary source warrant', reviewed=term['modified']) for u in term['provenance'].get('source_urls', []) if _url(u)])
        for rel in ('broader', 'narrower', 'related'):
            for target in term.get(rel, []):
                if target in terms:
                    row['relationships'].append(_edge(rel, 'concept:' + target, origin + '/vocabulary.html#' + target, row['url'], 'Local editorial vocabulary relationship.'))
        for rid in term['provenance'].get('record_ids', []):
            if str(rid) in by_id:
                row['relationships'].append(_edge('assigned to publication', 'publication:' + str(rid), origin + '/items/' + str(rid) + '.html', row['url'], 'Editorial access term, not an external authority assignment.'))
        row['search_text'] = ' '.join(_texts([row['title'], row['summary'], row['scope_note']] + row['aliases'] + row['identifiers']))
        rows.append(row)

    for programme in public_programmes:
        pid = _slug(urlsplit(programme['url']).path.rstrip('/').split('/')[-1])
        row = _record('programme:' + pid, 'programme', programme['title'], origin + '/programmes.html#' + pid, programme.get('description') or programme.get('summary') or programme.get('status', ''))
        row.update(identity=programme['url'], status=programme.get('status', ''), identifiers=_texts([programme.get(k) for k in ('pirr_reference', 'pirr_project_id')]),
                   sources=[_source(programme['source_url'], 'Published programme record', reviewed=programme['reviewed'])])
        for rid, record in by_id.items():
            for link in record.get('research_programmes', []):
                if link.get('url') == programme['url'] and _url(link.get('source_url')):
                    row['relationships'].append(_edge(link.get('relation_label') or link.get('relation') or 'source-linked publication', 'publication:' + rid, origin + '/items/' + rid + '.html', link['source_url']))
                    next(r for r in rows if r['id'] == 'publication:' + rid)['relationships'].append(_edge(link.get('relation_label') or link.get('relation') or 'source-linked programme', row['id'], row['url'], link['source_url']))
        row['search_text'] = ' '.join(_texts([row['title'], row['summary']] + row['identifiers']))
        rows.append(row)

    for page in ghost_records:
        address = _url(page.get('url'))
        parsed = urlsplit(address)
        if (page.get('public') is not True or not _public(page) or not page.get('title')
                or parsed.netloc != 'www.museumofone.art' or parsed.query or parsed.fragment
                or page.get('source_url') != address or not page.get('reviewed')
                or not re.fullmatch(r'[a-f0-9]{64}', str(page.get('source_sha256', '')))):
            raise ValueError('Website discovery record lacks checked public-source evidence: ' + str(page.get('url')))
        page_id = 'website:' + sha256(address.encode()).hexdigest()[:24]
        row = _record(page_id, 'website', page['title'], address, page.get('summary') or page.get('excerpt') or '')
        row.update(identity=address, date=page.get('date', ''), date_role=page.get('date_role', ''),
                   resource_type=page.get('record_type', 'Public website page'),
                   sources=[_source(address, 'Public Ghost page', reviewed=page['reviewed'], sha256=page['source_sha256'])],
                   search_text=' '.join(_texts([page['title'], row['summary'], page.get('text'), page.get('author')])),
                   source_sha256=page['source_sha256'])
        for rid, record in by_id.items():
            if str(record.get('institutional_url', '')).rstrip('/') == address.rstrip('/'):
                scope = record.get('institutional_match_scope') or institutional_scope(record)
                scope_notes = {
                    'exact_edition': 'The reviewed website metadata explicitly links this deposited edition DOI. Web and edition publication dates remain separate.',
                    'version_family': 'The reviewed website metadata links the concept DOI for this version family; an exact deposited-edition match is not established.',
                    'work': 'The catalogue links this website description at work level; a match to the particular deposited edition is not established.',
                }
                if scope not in scope_notes:
                    raise ValueError('Unsupported institutional match scope: ' + str(scope))
                row['relationships'].append(_edge('website description linked to catalogue publication', 'publication:' + rid, origin + '/items/' + rid + '.html', address, scope_notes[scope], institutional_match_scope=scope, evidence_scope=scope))
                next(r for r in rows if r['id'] == 'publication:' + rid)['relationships'].append(_edge('institutional web description', page_id, address, address, scope_notes[scope], institutional_match_scope=scope, evidence_scope=scope))
        rows.append(row)

    # Relationships only target exported records. This also prevents private
    # contextual nodes from leaking through a public publication's links.
    exported = {r['id'] for r in rows}
    titles = {r['id']: r['title'] for r in rows}
    for row in rows:
        row['relationships'] = [e for e in row['relationships'] if e['target_id'] in exported]
        for edge in row['relationships']:
            edge['target_title'] = titles[edge['target_id']]
    return _finish(rows, origin, counts=dict(Counter(r['kind'] for r in rows)))


def build_fulltext_index(records, root, origin):
    """Extract the provided, public corpus without OCR, editing or paraphrase.

    Whitespace is preserved in text; excerpts are verbatim slices rendered as
    text nodes. Source fixity, page extent, attribution and individual licences
    travel with every document manifest. No publication licence is replaced by
    a new licence for the derived index.
    """
    import fitz
    origin = _origin(origin)
    by_id = _eligible(records, root)
    rows, documents = [], []
    for rid, record in by_id.items():
        copy = record.get('reading_copy')
        if not copy:
            continue
        path = Path(root) / 'dist/assets/documents' / (rid + '.pdf')
        content = path.read_bytes()
        digest = sha256(content).hexdigest()
        if digest != copy['sha256'] or len(content) != copy['bytes']:
            raise ValueError('Full-text source fixity mismatch: ' + rid)
        if not _url(record.get('license', {}).get('url')):
            raise ValueError('Full-text source lacks rights statement: ' + rid)
        manifest = dict(id=rid, title=record['title'], author=record.get('author', ''), source_url=copy['source_url'],
                        pdf_url=origin + '/assets/documents/' + rid + '.pdf', sha256=digest,
                        license=record['license'], method='PyMuPDF text-layer extraction, sort=False; no OCR, rewriting or inferred corrections.',
                        extraction_version=fitz.VersionBind, publication_eligibility='public source snapshot verified',
                        rights_profile='User-authorized search access to supplied public corpus; original item licences and attribution retained.', pages=[])
        with fitz.open(stream=content, filetype='pdf') as pdf:
            if len(pdf) != copy['page_count']:
                raise ValueError('Full-text page extent mismatch: ' + rid)
            for index, page in enumerate(pdf):
                text = page.get_text('text', sort=False)
                number = index + 1
                quality = {'characters': len(text), 'replacement_characters': text.count('\ufffd'),
                           'status': 'text-layer' if len(text.strip()) >= 20 else 'sparse-or-empty-text',
                           'reading_order_reviewed': False}
                manifest['pages'].append({'page': number, **quality})
                if not text.strip():
                    continue
                chapter = next((p for p in record.get('contents', []) if p['pdf_start'] <= number <= p['pdf_end']), None)
                row = _record('passage:' + rid + ':' + str(number), 'passage', record['title'] + ' — PDF page ' + str(number), origin + '/read/' + rid + '.html#page=' + str(number))
                row.update(text=text, parent_id='publication:' + rid, parent_title=record['title'], page=number,
                           author=record.get('author', ''), date=record.get('date', ''), collection=record.get('collection', ''),
                           document_id=rid, source_sha256=digest, quality=quality, license=record['license'],
                           sources=[_source(manifest['pdf_url'] + '#page=' + str(number), 'Original deposited PDF, file page ' + str(number))],
                           relationships=[_edge('passage in edition', 'publication:' + rid, origin + '/items/' + rid + '.html', manifest['pdf_url'] + '#page=' + str(number))])
                if chapter:
                    row['chapter_id'] = 'chapter:' + rid + ':' + chapter['id']
                    row['chapter_title'] = chapter['title']
                    row['relationships'].append(_edge('within checked chapter extent', row['chapter_id'], origin + '/' + chapter['url'], manifest['pdf_url'] + '#page=' + str(number), 'Pagination containment; no inferred topical relationship.', target_title=chapter['title']))
                row['relationships'][0]['target_title'] = record['title']
                rows.append(row)
        manifest['page_count'] = copy['page_count']
        documents.append(manifest)
    return _finish(rows, origin, 'passages', documents=documents, counts=dict(documents=len(documents), pages=sum(d['page_count'] for d in documents), searchable_pages=len(rows)))


def build_discovery_page(write, layout, feed, origin):
    e = lambda x: escape(str(x), quote=True)
    kinds = [('publication', 'Publications'), ('chapter', 'Chapters & essays'), ('entity', 'People, artworks & events'), ('concept', 'Concepts & subjects'), ('programme', 'Research programmes'), ('website', 'Writing & website pages'), ('passage', 'Source passages only')]
    choices = ''.join('<option value="' + k + '">' + label + '</option>' for k, label in kinds)
    fallback = ''.join('<li><a href="' + e(row['url'][len(origin) + 1:] if row['url'].startswith(origin + '/') else row['url']) + '">' + e(row['title']) + '</a><small>' + e(row['kind']) + '</small></li>' for row in feed['records'])
    body = '''<div class="page-head"><div class="eyebrow">Connected research discovery</div><h1>Follow an idea through the archive.</h1><p>Find a publication, a chapter, a person, an artwork or a concept. Each connection leads back to its source.</p></div>'''
    body += '''<section class="research-discovery" data-research-discovery data-sync-url="true" data-local-results="true" data-archive-origin="''' + e(origin) + '''" data-index-snapshot="metadata/research-discovery.v2.json" data-passages-url="metadata/research-passages.v2.json"><form class="discovery-form" data-discovery-form method="get" action="research-discovery.html"><label for="research-query">Search titles, names, identifiers and concepts</label><input id="research-query" type="search" name="q" autocomplete="off"><div class="discovery-controls"><label for="research-kind">Look in</label><select id="research-kind" name="kind"><option value="">All records</option>''' + choices + '''</select><label><input type="checkbox" name="fulltext"> Also search passages in the publications</label><button type="submit">Search</button></div></form><p class="discovery-status" data-discovery-status role="status" aria-live="polite">Browse the linked records below or search the catalogue.</p><ol class="discovery-results" data-discovery-results></ol><button class="discovery-more" type="button" data-discovery-more hidden>Show more results</button><p class="discovery-evidence">Passages come from the original PDF text layer and link to the exact file page. Extraction order may differ from the printed layout. Publication licences and attribution remain attached to the originals.</p><p><a href="catalogue.html">Browse publication records</a> · <a href="contents.html">Browse chapters</a> · <a href="vocabulary.html">Explore concepts</a> · <a href="https://www.museumofone.art/">Search writing on Museum of One</a></p></section>'''
    body += '<details class="discovery-fallback"><summary>Browse every described record</summary><ul>' + fallback + '</ul></details>'
    body += '<noscript><p>The search controls need JavaScript. All described records remain available in the browse list above.</p></noscript>'
    html = layout('Research discovery', 'Search publications, chapters, people, artworks, concepts and verified source passages.', body, 'research-discovery.html')
    html = html.replace('</head>', '<script defer src="assets/research-discovery.js"></script></head>')
    write('research-discovery.html', html)
    return ['research-discovery.html']
