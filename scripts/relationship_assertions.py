"""Typed, evidence-bearing assertions shared by discovery and metadata exports."""
from copy import deepcopy
import hashlib
import json
from identities import DEFAULT_ORIGIN, doi_uri, entity_uri, institutional_scope, institutional_target, work_uri

RELATIONS = {
    'author': {'id': 'authored-by', 'inverse': 'author-of', 'range': ['Person', 'Organization']},
    'publisher': {'id': 'published-by', 'inverse': 'publisher-of', 'range': ['Organization']},
    'artist discussed': {'id': 'discusses-artist', 'inverse': 'artist-discussed-in', 'range': ['Person']},
    'artwork discussed': {'id': 'discusses-artwork', 'inverse': 'artwork-discussed-in', 'range': ['Artwork']},
    'exhibition discussed': {'id': 'discusses-exhibition', 'inverse': 'exhibition-discussed-in', 'range': ['Exhibition']},
    'scholar discussed': {'id': 'discusses-scholar', 'inverse': 'scholar-discussed-in', 'range': ['Person']},
    'curator discussed': {'id': 'discusses-curator', 'inverse': 'curator-discussed-in', 'range': ['Person']},
    'scholarly correspondent': {'id': 'has-scholarly-correspondent', 'inverse': 'correspondent-in', 'range': ['Person']},
}
ENTITY_RELATIONS = {
    'created by': {'id': 'created-by', 'inverse': 'creator-of', 'domain': ['Artwork'], 'range': ['Person', 'Organization']},
    'curator discussed in connection with exhibition': {
        'id': 'curator-discussed-with-exhibition', 'inverse': 'exhibition-discussed-with-curator',
        'domain': ['Exhibition'], 'range': ['Person']},
}


def predicate_uri(key, origin=DEFAULT_ORIGIN):
    return origin.rstrip('/') + '/metadata/relations.json#' + key


def _assertion(subject, predicate, target, source, scope, reviewed=None, location=None, note='', reviewer=None):
    identity = json.dumps([subject, predicate, target, source], ensure_ascii=False, separators=(',', ':'))
    return {
        'id': 'urn:museum-of-one:assertion:' + hashlib.sha256(identity.encode()).hexdigest(),
        'subject': subject, 'predicate': predicate, 'object': target,
        'scope': scope, 'status': 'source_corroborated_context',
        'source_url': source,
        'source_location': deepcopy(location) if location else {'kind': 'web_page', 'url': source, 'precision': 'page'},
        'reviewed': reviewed, 'reviewer': reviewer,
        'unknowns': [key for key, value in [('reviewed', reviewed), ('reviewer', reviewer)] if not value],
        'note': note,
    }


def typed_relationship_assertions(record, origin=DEFAULT_ORIGIN):
    result = []
    scope = institutional_scope(record)
    meta = record.get('institutional_metadata') or {}
    # Contextual relationships describe the work unless the linked evidence
    # expressly supplies a narrower verified passage/edition scope.
    for link in record.get('entity_links', []):
        label = link.get('relation', '')
        if label not in RELATIONS:
            raise ValueError('Unregistered entity relationship: ' + label)
        relation = RELATIONS[label]
        if link.get('entity_type') not in relation['range']:
            raise ValueError('Wrong entity type for relationship ' + label)
        source = link.get('source_url')
        if not source:
            raise ValueError('Relationship lacks source evidence: ' + label)
        assertion_scope = link.get('evidence_scope', 'work')
        subject = doi_uri(record['doi']) if assertion_scope == 'exact_edition' else work_uri(record, origin)
        result.append(_assertion(
            subject, predicate_uri(relation['id'], origin), entity_uri(link['id'], origin), source,
            assertion_scope, link.get('reviewed') or (meta.get('reviewed') if source == meta.get('source_url', record.get('institutional_url')) else None),
            link.get('source_location'), link.get('note', ''), link.get('reviewer'),
        ))
    if record.get('institutional_url'):
        result.append(_assertion(
            record['institutional_url'], predicate_uri('describes', origin), institutional_target(record, origin),
            meta.get('source_url') or record['institutional_url'], scope, meta.get('reviewed'),
            {'kind': 'metadata_field', 'field': 'linked_zenodo_dois', 'values': deepcopy(meta.get('linked_zenodo_dois', []))},
            'Exact-edition matching requires the selected DOI in the reviewed page metadata; other matches retain their wider scope.',
        ))
    return result


def typed_entity_relationship_assertions(entities, origin=DEFAULT_ORIGIN):
    """Preserve entity-to-entity relationships and their own evidence dates."""
    by_id = {entity['id']: entity for entity in entities}
    result = []
    for entity in entities:
        for link in entity.get('relationships', []):
            relation = ENTITY_RELATIONS.get(link.get('relation'))
            target = by_id.get(link.get('id'))
            if not relation or not target or entity['type'] not in relation['domain'] or target['type'] not in relation['range']:
                raise ValueError('Unsupported contextual entity relationship: ' + str(link))
            if not link.get('source_url'):
                raise ValueError('Entity relationship lacks source evidence')
            result.append(_assertion(entity_uri(entity['id'], origin), predicate_uri(relation['id'], origin),
                                     entity_uri(target['id'], origin), link['source_url'], 'contextual_entity',
                                     link.get('reviewed'), link.get('source_location'), link.get('note', ''), link.get('reviewer')))
    return result


def relation_register(origin=DEFAULT_ORIGIN):
    return {'profile_version': '3.0.0', 'scope': 'Museum of One local relationship vocabulary; no external approval implied.',
            'relations': [dict(definition, label=label, uri=predicate_uri(definition['id'], origin),
                               domain=['Work'], evidence_required=True) for label, definition in RELATIONS.items()]
            + [dict(definition, label=label, uri=predicate_uri(definition['id'], origin), evidence_required=True)
               for label, definition in ENTITY_RELATIONS.items()]
            + [{'id': 'describes', 'label': 'describes', 'uri': predicate_uri('describes', origin),
                'inverse': 'described-by', 'domain': ['WebPage'], 'range': ['Work', 'Edition', 'VersionFamily'], 'evidence_required': True}]}
