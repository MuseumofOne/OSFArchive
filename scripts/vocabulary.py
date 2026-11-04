"""Local, source-qualified discovery vocabulary and SKOS export.

The local scheme is an editorial access layer. It never rewrites deposited
keywords or implies that a local concept has been accepted by an external body.
"""
from copy import deepcopy
from html import escape
import json
from urllib.parse import quote


def _terms(vocab):
    return vocab.get('terms', [])


def _url(term, vocab, origin=None):
    base = origin.rstrip('/') + '/vocabulary.html' if origin else vocab['scheme']['base_uri']
    return base + '#' + term['id']


def _descriptor(term, vocab, assignment_field):
    return {
        'id': term['id'], 'label': term['preferred_label'],
        'uri': _url(term, vocab), 'url': 'vocabulary.html#' + term['id'],
        'persistent_id': term['persistent_id'],
        'scheme': vocab['scheme']['id'], 'scheme_version': vocab['scheme']['version'],
        'alternative_labels': deepcopy(term['alternative_labels']),
        'definition': term['definition'], 'scope_note': term['scope_note'],
        'kind': term['kind'], 'broader': list(term['broader']),
        'narrower': list(term['narrower']), 'related': list(term['related']),
        'mapping_status': term['mapping_status'],
        'external_mappings': deepcopy(term['external_mappings']),
        'assignment_provenance': {
            'status': 'local_editorial_access_term',
            'input_field': assignment_field,
            'editorial_owner': vocab['scheme']['editorial_owner'],
            'reviewed': vocab['scheme']['modified'],
        },
    }


def attach_vocabulary(records, vocab):
    """Return copied records with controlled subjects/genres; retain source data.

    Unknown terms fail the build instead of silently creating undocumented
    concepts. Adding holdings therefore requires an explicit vocabulary review.
    """
    subjects = {}
    genres = {}
    for term in _terms(vocab):
        target = genres if term['kind'] == 'genre' else subjects
        for label in [term['preferred_label']] + term['alternative_labels']:
            target[label.casefold()] = term
    result = []
    for raw in records:
        record = deepcopy(raw)
        controlled = []
        for label in raw.get('subjects', []):
            term = subjects.get(label.casefold())
            if term is None:
                raise ValueError('Undocumented editorial subject: ' + label)
            if term['id'] not in {t['id'] for t in controlled}:
                controlled.append(_descriptor(term, vocab, 'subjects'))
        record['controlled_subjects'] = controlled
        genre = genres.get(str(raw.get('type', '')).casefold())
        if raw.get('type') and genre is None:
            raise ValueError('Undocumented resource genre: ' + raw['type'])
        record['genre_terms'] = [_descriptor(genre, vocab, 'type')] if genre else []
        record['vocabulary_version'] = vocab['scheme']['version']
        result.append(record)
    return result


def vocabulary_graph(vocab, origin):
    """Export documented local concepts; only checked mappings become SKOS links."""
    scheme = vocab['scheme']
    by_id = {term['id']: term for term in _terms(vocab)}
    scheme_uri = origin.rstrip('/') + '/vocabulary.html'
    graph = [{
        '@id': scheme_uri, '@type': 'skos:ConceptScheme',
        'dct:title': scheme['title'], 'dct:description': scheme['scope_note'],
        'dct:publisher': scheme['editorial_owner'],
        'dct:modified': {'@value': scheme['modified'], '@type': 'xsd:date'},
        'owl:versionInfo': str(scheme['version']),
        'skos:hasTopConcept': [{'@id': _url(t, vocab, origin)} for t in _terms(vocab) if not t['broader']],
    }]
    for term in _terms(vocab):
        node = {
            '@id': _url(term, vocab, origin), '@type': 'skos:Concept',
            'dct:identifier': term['persistent_id'],
            'skos:inScheme': {'@id': scheme_uri},
            'skos:prefLabel': {'@value': term['preferred_label'], '@language': 'en'},
            'skos:altLabel': [{'@value': label, '@language': 'en'} for label in term['alternative_labels']],
            'skos:definition': {'@value': term['definition'], '@language': 'en'},
            'skos:scopeNote': {'@value': term['scope_note'], '@language': 'en'},
            'skos:editorialNote': term['mapping_note'],
            'dct:source': [{'@id': url} for url in term['provenance']['source_urls']],
            'dct:modified': {'@value': term['modified'], '@type': 'xsd:date'},
            'dct:publisher': term['editorial_owner'],
        }
        for relationship in ('broader', 'narrower', 'related'):
            if term[relationship]:
                node['skos:' + relationship] = [{'@id': _url(by_id[x], vocab, origin)} for x in term[relationship]]
        if not term['broader']:
            node['skos:topConceptOf'] = {'@id': scheme_uri}
        for mapping in term['external_mappings']:
            if mapping.get('status') == 'verified':
                node.setdefault('skos:' + mapping['relation'], []).append({'@id': mapping['uri']})
        graph.append(node)
    return {'@context': {
        'skos': 'http://www.w3.org/2004/02/skos/core#',
        'dct': 'http://purl.org/dc/terms/',
        'owl': 'http://www.w3.org/2002/07/owl#',
        'xsd': 'http://www.w3.org/2001/XMLSchema#',
    }, '@graph': graph}


def build_vocabulary_pages(records, vocab, write, layout, origin):
    """Write the public term register and reusable JSON/SKOS; return HTML paths."""
    e = lambda value: escape(str(value), quote=True)
    terms = sorted(_terms(vocab), key=lambda t: t['preferred_label'].casefold())
    by_id = {t['id']: t for t in terms}
    attached = attach_vocabulary(records, vocab)
    subject_count = sum(t['kind'] != 'genre' for t in terms)
    scheme = vocab['scheme']
    body = f'''<div class="page-head"><div class="breadcrumb"><a href="index.html">Archive</a> / <a href="subjects.html">Subjects</a> / Controlled vocabulary</div><div class="eyebrow">Discovery / Term authority register</div><h1>Words with a record.</h1><p>{subject_count} subject access terms and {len(terms)-subject_count} resource genres, with local definitions, relationships, and accountable editorial provenance.</p></div>
<section class="reading item-section"><h2>How to use this register</h2><p>{e(scheme['scope_note'])}</p><p>Preferred terms support consistent discovery. Alternative labels lead to the same concept. Broader and narrower terms express local hierarchy; related terms connect distinct ideas. Named subjects are access points and link to separate entity authority records where available.</p><p>Original Zenodo keywords remain in each item’s source metadata. These controlled terms describe the archive’s editorial access layer. An external reference is never an assertion that the entire local vocabulary has been approved by that institution.</p><p><a href="metadata/vocabulary.jsonld" download>Download SKOS JSON-LD</a> · <a href="metadata/vocabulary.json" download>Download the full term register</a> · <a href="catalogue.html">Search the catalogue</a></p></section>
<div class="note-box"><strong>Vocabulary edition {e(scheme['version'])}</strong> · Reviewed {e(scheme['modified'])}<br>Editorial owner: {e(scheme['editorial_owner'])}. {e(scheme['maintenance_note'])}</div>
<div class="searchbar"><label class="sr-only" for="vocabulary-filter">Find a term or alternative label</label><input id="vocabulary-filter" type="search" placeholder="Find a term, synonym, or scope…" autocomplete="off"></div><p id="vocabulary-count" role="status" aria-live="polite">{len(terms)} terms</p>
<nav class="programme-badges" aria-label="Vocabulary terms">'''
    body += ''.join(f'<a class="programme-badge" href="#{e(t["id"])}">{e(t["preferred_label"])}</a>' for t in terms) + '</nav><div id="vocabulary-register">'

    def term_links(ids):
        return ' · '.join(f'<a href="#{e(i)}">{e(by_id[i]["preferred_label"])}</a>' for i in ids) or '—'

    for term in terms:
        linked = [r for r in attached if any(x['id'] == term['id'] for x in r['controlled_subjects'] + r['genre_terms'])]
        records_html = ''.join(f'<li><a href="items/{e(r["id"])}.html">{e(r["title"])}</a> <small>{e(r["accession"])}</small></li>' for r in linked)
        mappings = ''.join(f'<li><a href="{e(m["source_url"])}">{e(m["vocabulary"])}: {e(m["label"])}</a> · {e(m["relation"])} · checked {e(m["verified_on"])}<p>{e(m["note"])}</p></li>' for m in term['external_mappings'])
        if not mappings:
            mappings = '<li>No external equivalence asserted. This term is controlled within the local scheme.</li>'
        search = ' '.join([term['preferred_label'], *term['alternative_labels'], term['definition'], term['scope_note']]).casefold()
        body += f'''<article class="vocabulary-term item-section" id="{e(term['id'])}" data-vocabulary-search="{e(search)}"><div class="eyebrow">{e(term['kind'].replace('-', ' '))} / {e(term['id'])}</div><h2>{e(term['preferred_label'])}</h2><p>{e(term['definition'])}</p><dl class="metadata"><div><dt>Use for</dt><dd>{e('; '.join(term['alternative_labels']) or 'No alternative label recorded')}</dd></div><div><dt>Scope note</dt><dd>{e(term['scope_note'])}</dd></div><div><dt>Broader terms</dt><dd>{term_links(term['broader'])}</dd></div><div><dt>Narrower terms</dt><dd>{term_links(term['narrower'])}</dd></div><div><dt>Related terms</dt><dd>{term_links(term['related'])}</dd></div><div><dt>Persistent local identifier</dt><dd><code>{e(term['persistent_id'])}</code></dd></div><div><dt>External alignment</dt><dd><ul class="source-list">{mappings}</ul></dd></div><div><dt>Term provenance</dt><dd>{e(term['provenance']['note'])} Definition and scope: local editorial description. Reviewed {e(term['modified'])} by {e(term['editorial_owner'])}.</dd></div></dl><details><summary>Explore {len(linked)} linked catalogue {'record' if len(linked)==1 else 'records'}</summary><ul class="source-list">{records_html or '<li>No current assignment.</li>'}</ul></details><p><a href="#{e(term['id'])}">Permalink to this term</a></p></article>'''
    body += '''</div><p id="vocabulary-empty" hidden>No terms match. Try a shorter word.</p><script>(function(){const input=document.getElementById('vocabulary-filter');const terms=Array.from(document.querySelectorAll('.vocabulary-term'));const count=document.getElementById('vocabulary-count');input.addEventListener('input',function(){const query=input.value.trim().toLocaleLowerCase();let found=0;terms.forEach(function(term){const show=term.dataset.vocabularySearch.includes(query);term.hidden=!show;if(show)found++});count.textContent=found+' of '+terms.length+' terms';document.getElementById('vocabulary-empty').hidden=found!==0});window.addEventListener('hashchange',function(){if(input.value){input.value='';input.dispatchEvent(new Event('input'))}})})();</script>'''
    graph = vocabulary_graph(vocab, origin)
    write('vocabulary.html', layout('Controlled vocabulary', 'Museum of One subject and genre authority register: preferred terms, definitions, synonyms, relationships, provenance, and SKOS export.', body, 'vocabulary.html', schema=graph))
    write('metadata/vocabulary.json', json.dumps(vocab, ensure_ascii=False, indent=2))
    write('metadata/vocabulary.jsonld', json.dumps(graph, ensure_ascii=False, indent=2))
    return ['vocabulary.html']
