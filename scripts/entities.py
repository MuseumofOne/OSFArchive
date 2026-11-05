"""Source-qualified contextual authorities and reciprocal discovery pages.

Entity links describe the relation evidenced by a particular source. Subject
artists, correspondents and curators are never promoted to publication authors.
"""
from copy import deepcopy
from html import escape
import re
from identities import entity_uri, doi_uri
from relationship_assertions import RELATIONS


def _entities(value):
    return value.get('entities', []) if isinstance(value, dict) else value


def _e(value):
    return escape(str(value or ''), quote=True)


def _validate(entities):
    ids = set()
    for entity in entities:
        eid = entity['id']
        if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', eid) or eid in ids:
            raise ValueError(f'Invalid or duplicate contextual entity id: {eid}')
        if entity['type'] not in {'Person', 'Organization', 'Artwork', 'Exhibition'}:
            raise ValueError(f'Unsupported entity type: {entity["type"]}')
        ids.add(eid)
    for entity in entities:
        for relationship in entity.get('relationships', []):
            if relationship['id'] not in ids:
                raise ValueError(f'Unknown related entity: {relationship["id"]}')


def attach_entities(records, entities):
    """Return independent record copies with explicit, evidence-linked relations."""
    entities = _entities(entities)
    _validate(entities)
    result = deepcopy(records)
    by_record = {str(record['id']): record for record in result}
    for record in result:
        record['entity_links'] = []
    for entity in entities:
        for link in entity.get('record_links', []):
            record = by_record.get(str(link['record_id']))
            if record is None:
                raise ValueError(f'Unknown entity-linked catalogue item: {link["record_id"]}')
            if link.get('relation') not in RELATIONS or entity['type'] not in RELATIONS[link['relation']]['range']:
                raise ValueError('Unsupported contextual relationship or entity type: ' + str(link.get('relation')))
            record['entity_links'].append({
                'id': entity['id'], 'label': entity['label'],
                'entity_type': entity['type'], 'relation': link['relation'],
                'source_url': link['source_url'], 'note': link.get('note', ''),
                'variants': deepcopy(entity.get('variants', [])),
                'evidence_scope': link.get('evidence_scope', 'work'),
                **{key: deepcopy(link[key]) for key in ('source_location', 'reviewed', 'reviewer') if key in link},
            })
    return result


def entity_link_panel(record, base='../'):
    """Optional item-page panel; all hrefs respect the caller's document depth."""
    links = record.get('entity_links', [])
    if not links:
        return ''
    rows = ''.join(
        f'<li><a href="{_e(base)}entities/{_e(link["id"])}.html">{_e(link["label"])}</a>'
        f'<small>{_e(link["relation"])} · {_e(link["entity_type"])} · '
        f'<a href="{_e(link["source_url"])}">source evidence ↗</a></small></li>'
        for link in links
    )
    return ('<section class="item-section entity-context" id="linked-context">'
            '<h2>People, works &amp; institutional context</h2>'
            f'<ul class="source-list">{rows}</ul></section>')


def _nav(base=''):
    return ('<nav class="programme-badges entity-nav" aria-label="Contextual authority indexes">'
            f'<a class="pill" href="{base}people.html">People &amp; organizations</a>'
            f'<a class="pill" href="{base}artworks.html">Artworks discussed</a>'
            f'<a class="pill" href="{base}exhibitions.html">Exhibitions discussed</a></nav>')


def entity_graph(entities, origin):
    """The same authority nodes used by entity pages and the combined graph."""
    entities = _entities(entities)
    _validate(entities)
    by_id = {entity['id']: entity for entity in entities}
    nodes = []
    for entity in entities:
        path = f'entities/{entity["id"]}.html'
        schema_type = {'Artwork': 'CreativeWork', 'Exhibition': 'ExhibitionEvent'}.get(entity['type'], entity['type'])
        node = {'@context': 'https://schema.org', '@type': schema_type,
                '@id': entity_uri(entity['id'], origin), 'name': entity['label'],
                'description': entity.get('summary', f'Contextual record for {entity["label"]}.'),
                'url': origin.rstrip('/') + '/' + path}
        if entity.get('variants'):
            node['alternateName'] = entity['variants']
        if entity.get('identifiers'):
            node['identifier'] = [{'@type': 'PropertyValue', 'propertyID': i['scheme'], 'value': i['value']}
                                  for i in entity['identifiers']]
        creators = [r for r in entity.get('relationships', []) if r['relation'] == 'created by']
        if creators:
            node['creator'] = [{'@type': 'Person', '@id': entity_uri(r['id'], origin),
                                'name': by_id[r['id']]['label']} for r in creators]
        node['subjectOf'] = [{'@type': 'CreativeWork', '@id': origin.rstrip('/')+'/items/'+str(link['record_id'])+'.html#work'}
                             for link in entity.get('record_links', []) if link['relation'] in {'artist discussed', 'artwork discussed', 'exhibition discussed', 'scholar discussed', 'curator discussed'}]
        node['subjectOf'] += [{'@type': 'WebPage', '@id': link['url'], 'url': link['url'], 'description': link['note']} for link in entity.get('web_links', [])]
        nodes.append(node)
    return {'@context': 'https://schema.org', '@graph': nodes}


def build_entity_pages(records, entities, write, layout, origin):
    """Write indexes and individual authorities; return paths for the sitemap."""
    entities = _entities(entities)
    _validate(entities)
    by_id = {entity['id']: entity for entity in entities}
    by_record = {str(record['id']): record for record in records}
    authority_nodes = {node['@id']: node for node in entity_graph(entities, origin)['@graph']}
    paths = []
    indexes = [
        ('people.html', 'People & organizations', {'Person', 'Organization'},
         'Follow authors, artists, scholars, curators and publishers through the selected catalogue.'),
        ('artworks.html', 'Artworks discussed', {'Artwork'},
         'Find publications through the artworks and series they discuss.'),
        ('exhibitions.html', 'Exhibitions discussed', {'Exhibition'},
         'Trace named exhibitions discussed in the published criticism.'),
    ]
    scope = ('These local contextual records connect the publications and their subjects. '
             'Relationships are attributed to linked sources. Artwork and exhibition records '
             'describe subjects of research; they are not collection holdings or accessioned objects.')
    for path, title, types, description in indexes:
        selected = sorted((entity for entity in entities if entity['type'] in types),
                          key=lambda entity: entity['label'].casefold())
        body = (f'<header class="page-head"><div class="eyebrow">Contextual authority index</div>'
                f'<h1>{_e(title)}</h1><p>{_e(description)}</p></header>{_nav()}'
                f'<div class="reading"><p>{_e(scope)}</p></div>'
                '<div class="directory-grid entity-directory">')
        for entity in selected:
            count = len({str(link['record_id']) for link in entity.get('record_links', [])})
            body += (f'<article class="directory-entry" id="{_e(entity["id"])}">'
                     f'<div class="eyebrow">{_e(entity["type"])} · {count} linked publication'
                     f'{"s" if count != 1 else ""}</div>'
                     f'<h2><a href="entities/{_e(entity["id"])}.html">{_e(entity["label"])}</a></h2>'
                     f'<p>{_e(entity.get("summary", ""))}</p></article>')
        body += '</div>'
        write(path, layout(title, description, body, path=path))
        paths.append(path)
    for entity in entities:
        path = f'entities/{entity["id"]}.html'
        description = entity.get('summary', f'Contextual record for {entity["label"]}.')
        body = ('<div class="breadcrumb"><a href="../index.html">Archive</a> / '
                '<a href="../people.html">Contextual authorities</a></div>'
                f'<header class="page-head" id="entity"><div class="eyebrow">{_e(entity["type"])} · '
                f'Local contextual authority record</div><h1>{_e(entity["label"])}</h1>'
                f'<p>{_e(description)}</p></header>{_nav("../")}'
                '<section class="item-section"><h2>Identity &amp; description</h2>'
                '<dl class="metadata">'
                f'<div><dt>Record identifier</dt><dd>MOO-CTX-{_e(entity["id"])}</dd></div>'
                f'<div><dt>Entity type</dt><dd>{_e(entity["type"])}</dd></div>'
                f'<div><dt>Record status</dt><dd>{_e(entity.get("authority_status", "Local contextual record"))}</dd></div>')
        if entity.get('variants'):
            body += f'<div><dt>Source name variants</dt><dd>{_e("; ".join(entity["variants"]))}</dd></div>'
        for identifier in entity.get('identifiers', []):
            body += (f'<div><dt>{_e(identifier["scheme"])}</dt><dd>'
                     f'<a href="{_e(identifier["url"])}">{_e(identifier["value"])} ↗</a>'
                     f'<p>{_e(identifier.get("note", ""))}</p></dd></div>')
        body += '</dl></section>'
        related = list(entity.get('relationships', []))
        for other in entities:
            for relationship in other.get('relationships', []):
                if relationship['id'] == entity['id']:
                    inverse = {'created by': 'creator of',
                               'curator discussed in connection with exhibition': 'discussed in connection with exhibition'}.get(relationship['relation'], 'related contextual record')
                    related.append({**relationship, 'id': other['id'], 'relation': inverse})
        if related:
            body += '<section class="item-section"><h2>Related contextual records</h2><ul class="source-list">'
            for relationship in related:
                target = by_id[relationship['id']]
                body += (f'<li><a href="{_e(target["id"])}.html">{_e(target["label"])}</a>'
                         f'<small>{_e(relationship["relation"])} · '
                         f'<a href="{_e(relationship["source_url"])}">source evidence ↗</a></small></li>')
            body += '</ul></section>'
        body += '<section class="item-section">'
        if entity.get('record_links'):
            body += '<h2>Linked publications</h2>'
        for link in entity.get('record_links', []):
            record = by_record[str(link['record_id'])]
            body += (f'<div class="entity-publication"><a class="record-row" href="../items/{_e(record["id"])}.html">'
                     f'<span class="row-id">{_e(record["accession"])}</span><span>'
                     f'<h3>{_e(record.get("short_title", record["title"]))}</h3>'
                     f'<p>{_e(link["relation"])} · {_e(record["type"])}</p></span>'
                     '<span aria-hidden="true">↗</span></a>'
                     f'<p class="entity-evidence">{_e(link.get("note", ""))} '
                     f'<a href="{_e(link["source_url"])}">Read the source ↗</a></p></div>')
        if entity.get('web_links'):
            body += '<section class="item-section"><h2>Exchanges and research context</h2><ul class="source-list">'
            for link in entity['web_links']:
                body += (f'<li><a href="{_e(link["url"])}">{_e(link["relation"])} ↗</a>'
                         f'<p>{_e(link["note"])}</p><small>Status: {_e(link["status"])} · reviewed {_e(link["reviewed"])}</small></li>')
            body += '</ul></section>'
        body += '</section><section class="item-section"><h2>Sources &amp; record control</h2><ul class="source-list">'
        for source in entity.get('sources', []):
            body += (f'<li><a href="{_e(source["url"])}">{_e(source["label"])} ↗</a>'
                     f'<small>{_e(source.get("note", ""))}</small></li>')
        body += ('</ul><p>Compiled from the linked publication records. Description review: 5 November 2026. Individual evidence dates are recorded in the downloadable data. '
                 'No external authority identifier is assigned where one has not been established.</p>'
                 f'<p><a href="../metadata/entities.json" download>Download contextual authority data ↓</a></p></section>')
        node = authority_nodes[entity_uri(entity['id'], origin)]
        write(path, layout(entity['label'], description, body, path=path, base='../', schema=node))
        paths.append(path)
    return paths
