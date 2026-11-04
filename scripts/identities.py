"""Shared public identifiers and evidence-scoped identity decisions.

Page routes remain stable. An identifier for a thing is distinct from the page
describing it, and a work is distinct from a deposited version family.
"""
import re

DEFAULT_ORIGIN = 'https://archive.museumofone.art'


def doi_uri(value):
    value = re.sub(r'^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)', '', str(value or '').strip(), flags=re.I)
    return 'https://doi.org/' + value if value else ''


def item_uri(record, origin=DEFAULT_ORIGIN):
    return origin.rstrip('/') + '/items/' + str(record['id']) + '.html'


def work_uri(record, origin=DEFAULT_ORIGIN):
    return item_uri(record, origin) + '#work'


def catalogue_uri(record, origin=DEFAULT_ORIGIN):
    return item_uri(record, origin) + '#catalogue-record'


def entity_uri(identifier, origin=DEFAULT_ORIGIN):
    if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', str(identifier)):
        raise ValueError('Invalid local entity identifier: ' + str(identifier))
    return origin.rstrip('/') + '/entities/' + identifier + '.html#entity'


def responsibility_uri(record, relation, origin=DEFAULT_ORIGIN):
    """Resolve through a maintained local authority when one is attached.

    ORCID remains an attributed external identifier, rather than a second
    disconnected person node or an unsupported sameAs assertion.
    """
    matches = [link for link in record.get('entity_links', []) if link.get('relation') == relation]
    if len(matches) == 1:
        return entity_uri(matches[0]['id'], origin)
    return item_uri(record, origin) + '#' + relation


def institutional_scope(record):
    """An explicit DOI in reviewed page metadata controls edition matching."""
    metadata = record.get('institutional_metadata') or {}
    links = {doi_uri(value).lower() for value in metadata.get('linked_zenodo_dois', [])}
    if doi_uri(record.get('doi')).lower() in links:
        return 'exact_edition'
    if record.get('conceptdoi') and doi_uri(record['conceptdoi']).lower() in links:
        return 'version_family'
    return 'work'


def institutional_target(record, origin=DEFAULT_ORIGIN):
    scope = institutional_scope(record)
    if scope == 'exact_edition':
        return doi_uri(record.get('doi'))
    if scope == 'version_family':
        return doi_uri(record.get('conceptdoi'))
    return work_uri(record, origin)


def edition_isbn(record):
    """Only an explicitly evidenced edition/format allocation travels as ISBN.

    Existing title-level ISBNs remain visible in qualified catalogue metadata.
    Syntax validity and being a Book are not evidence of format allocation.
    """
    evidence = record.get('isbn_evidence') or {}
    if (record.get('isbn') and evidence.get('scope') == 'edition_format'
            and evidence.get('status') in {'source_verified', 'registry_verified'}
            and evidence.get('source_url') and evidence.get('reviewed')):
        return record['isbn']
    return None
