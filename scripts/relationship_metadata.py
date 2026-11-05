"""Qualified linked-context projections used by metadata exports."""
from identities import entity_uri, work_uri, DEFAULT_ORIGIN
from relationship_assertions import typed_relationship_assertions

RDF = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
PROV = "http://www.w3.org/ns/prov#"


def extend_graph(graph, r, itemurl, origin):
    nodes = graph['@graph']
    by_id = {n.get('@id'): n for n in nodes}
    edition = by_id.get('https://doi.org/' + r['doi'])
    catalogue = by_id.get(itemurl + '#catalogue-record')
    work = by_id.get(work_uri(r, origin), edition)
    if edition is None or catalogue is None:
        return graph
    if r.get('contents'):
        edition.setdefault('hasPart', []).extend({'@id': origin + '/' + p['url'] + '#component'} for p in r['contents'])
    assertions = typed_relationship_assertions(r, origin)
    for relation, assertion in zip(r.get('entity_links', []), assertions):
        identity = entity_uri(relation['id'], origin)
        catalogue.setdefault('mentions', []).append({'@id': identity})
        role = relation['relation'].lower().replace(' ', '_')
        subject = edition if assertion['scope'] == 'exact_edition' else work
        if role in ('artist_discussed', 'artwork_discussed', 'exhibition_discussed', 'scholar_discussed', 'curator_discussed'):
            subject.setdefault('about', []).append({'@id': identity})
        if role == 'scholarly_correspondent':
            subject.setdefault('mentions', []).append({'@id': identity})
        if role in ('author', 'publisher'):
            work[role] = {'@id': identity}
        nodes.append({
            '@type': ['CreativeWork', RDF + 'Statement'],
            '@id': itemurl + '#relationship-' + relation['id'] + '-' + role.replace('_', '-'),
            'identifier': assertion['id'], 'name': relation['relation'],
            'about': {'@id': identity}, 'isBasedOn': {'@id': assertion['source_url']},
            'description': assertion['note'] or 'Source-qualified contextual relationship.',
            RDF + 'subject': {'@id': assertion['subject']},
            RDF + 'predicate': {'@id': assertion['predicate']},
            RDF + 'object': {'@id': assertion['object']},
            PROV + 'wasDerivedFrom': {'@id': assertion['source_url']},
        })
    if r.get('controlled_subjects'):
        oldrefs = catalogue.get('about', [])
        oldrefs = oldrefs if isinstance(oldrefs, list) else [oldrefs]
        catalogue['about'] = [ref for ref in oldrefs if ref.get('@id') == 'https://doi.org/' + r['doi']]
        termset_id = origin + '/vocabulary.html'
        nodes.append({'@type': 'DefinedTermSet', '@id': termset_id, 'name': 'Museum of One local editorial discovery vocabulary',
                      'url': termset_id, 'description': 'Published preferred labels, definitions, alternative labels and qualified external mappings.'})
        for term in r['controlled_subjects']:
            term_id = origin + '/' + term['url']
            nodes.append({'@type': 'DefinedTerm', '@id': term_id, 'name': term['label'], 'termCode': term['id'],
                          'description': term.get('definition', ''), 'inDefinedTermSet': {'@id': termset_id}})
            catalogue['about'].append({'@id': term_id})
        graph['@graph'] = [n for n in nodes if not (n.get('@type') in ('DefinedTerm', 'DefinedTermSet') and '/subjects.html#' in n.get('@id', ''))]
    for context in r.get('pirr_references', []):
        node = next((n for n in graph['@graph'] if n.get('@id') == context['programme_url']), None)
        if node is not None:
            node['identifier'] = [{'@type': 'PropertyValue', 'propertyID': i['scheme'], 'value': i['value'], 'url': i['source_url']} for i in context.get('identifiers', [])]
    return graph


def relationship_assertions(r):
    result = []
    typed = typed_relationship_assertions(r, r.get('metadata_origin', DEFAULT_ORIGIN))
    for link, assertion in zip(r.get('entity_links', []), typed):
        result.append({'field': 'entity_link:' + link['id'] + ':' + link['relation'], 'value': link,
                       'source_url': link.get('source_url') or r['institutional_url'],
                       'status': 'institutional_context_relationship',
                       'note': 'Contextual role is source-qualified; subject artists and referenced scholars are not publication coauthors.',
                       'assertion': assertion})
    notes = [
        ('contents', 'Analytic descriptions were checked against headings and pagination in the deposited PDF. Component records do not have independent deposits or DOIs.'),
        ('controlled_subjects', 'Local preferred terms with definitions and synonyms. External alignment is scoped in the vocabulary register.'),
        ('genre_terms', 'Local resource-genre classification. Digital file format is recorded separately.'),
        ('archival_context', 'Provenance records what is documented and leaves unknown custody and original order explicit.'),
        ('description_history', 'Catalogue description events; these are not work publication dates or acquisition dates.'),
    ]
    for field, note in notes:
        if r.get(field):
            result.append({'field': field, 'value': r[field],
                           'source_url': (r.get('reading_copy') or {}).get('source_url', r['zenodo_url']) if field == 'contents' else r.get('description_policy_url') or r['institutional_url'],
                           'status': 'derived_file_inspection' if field == 'contents' else 'editorial_description_control',
                           'note': note})
    if r.get('pirr_references'):
        result.append({'field': 'pirr_references', 'value': r['pirr_references'], 'source_url': r['institutional_url'],
                       'status': 'institutional_context_relationship',
                       'note': 'PIRR project IDs and programme references identify research records, not publication versions or independent chapter deposits.'})
    if typed:
        result.append({'field': 'relationship_assertions', 'value': typed, 'status': 'typed_evidence_projection',
                       'note': 'Stable, typed assertions retain source scope and explicit unknown review metadata.'})
    return result
