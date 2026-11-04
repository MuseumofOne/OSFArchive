"""Versioned, public-only discovery contract for a native Ghost archive entrance.

Build integration (after all catalogue enrichments, including attach_pirr)::

    from integration_search import (
        build_search_index, encode_search_index, load_source_snapshots,
        searchable_text,
    )
    snapshots = load_source_snapshots(RECORDS, DATA / 'source')
    feed = build_search_index(RECORDS, ORIGIN, snapshots)
    write('metadata/search-index.v1.json', encode_search_index(feed))

Use ``searchable_text(record)`` for each catalogue card's ``data-search`` as well,
so the native entrance and standalone archive share discovery scope. The existing
discovery.json reading-list contract is independent and must remain unchanged.

``content_version`` is SHA-256 of canonical JSON of every other payload field.
It changes with public content, source-review dates or canonical origin, not the
clock or input order. Dates are supplied catalogue/source dates; no build time is
presented as a publication or record-modification date. ``date`` in each result
retains the catalogue's repository-publication date and precision.

Consumers must check schema_version == 1, use result.url as the destination, and
render strings as text. Search uses NFKD/accent-insensitive all-term matching,
as ArchiveCore already does. Group/year/subject/type/programme filters map to
collection/date[:4]/subjects/type/programmes[].id. Identifiers inside programme
relationships identify programmes, never the publication. The feed is public;
fetch without credentials. Bundle a same-origin copy in the Ghost theme as a
fallback; verify actual deployed CORS headers before enabling remote refresh.
This module neither changes global Ghost search nor installs a Ghost template.
"""
from __future__ import annotations

from collections.abc import Mapping
from hashlib import sha256
import json
from pathlib import Path
import re
from urllib.parse import urlsplit

SCHEMA_VERSION = 1
PUBLIC_STATUS = 'Published source; selected catalogue record'
SCOPE = 'Selected public catalogue; not the complete institutional holdings.'


def _text(value):
    return ' '.join(str(value or '').split())


def _strings(values):
    return [_text(value) for value in values or [] if isinstance(value, str) and _text(value)] if isinstance(values, (list, tuple)) else []


def _objects(values):
    return [value for value in values if isinstance(value, Mapping)] if isinstance(values, (list, tuple)) else []


def _doi(value):
    return str(value or '').removeprefix('https://doi.org/')


def _public_url(value):
    """Exclude local files, credentials and non-web identifiers from URL fields."""
    if not isinstance(value, str) or any(ord(c) < 33 for c in value):
        return ''
    try:
        parsed = urlsplit(value)
        parsed.port  # Validate a supplied port rather than accepting a broken URL.
        if (parsed.scheme == 'https' and parsed.hostname and
                not parsed.username and not parsed.password):
            return value
    except ValueError:
        pass
    return ''


def _origin(value):
    origin = str(value).rstrip('/')
    parsed = urlsplit(origin)
    path = parsed.path
    if (not _public_url(origin) or parsed.query or parsed.fragment or
            not re.fullmatch(r'(?:/[A-Za-z0-9._~-]+)*', path) or
            any(segment in ('.', '..') for segment in path.split('/'))):
        raise ValueError('Search origin must be an absolute HTTPS base URL without query, fragment or traversal')
    return origin


def public_export_eligible(record, source):
    """Fail closed on unknown status, missing source or contradictory access flags.

    Version 1 exports the current Zenodo-backed publication items only. Adding a
    different repository or descriptive level requires an explicit new policy,
    rather than silently treating every future catalogue object as public.
    A public source snapshot is historical evidence, not a live access check.
    """
    if not isinstance(record, Mapping) or not isinstance(source, Mapping):
        return False
    rid = str(record.get('id') or '')
    if not re.fullmatch(r'[1-9][0-9]*', rid):
        return False
    if (record.get('record_status') != PUBLIC_STATUS or
            record.get('record_level') != 'Item'):
        return False
    if any(record.get(key) not in (None, False) for key in ('private', 'draft', 'is_draft', 'hidden')):
        return False
    if any(record.get(key) not in (None, True) for key in ('public', 'published', 'is_published')):
        return False
    if record.get('visibility') not in (None, 'public'):
        return False
    if record.get('access_right') not in (None, 'open'):
        return False
    if (str(source.get('id')) != rid or source.get('submitted') is not True or
            source.get('state') != 'done' or source.get('is_published') is False):
        return False
    metadata = source.get('metadata')
    if not isinstance(metadata, Mapping) or metadata.get('access_right') != 'open':
        return False
    access = source.get('access')
    if access is not None and (not isinstance(access, Mapping) or
                               access.get('record') != 'public' or
                               access.get('files') not in (None, 'public')):
        return False
    return (_doi(record.get('doi')) == _doi(source.get('doi')) == '10.5281/zenodo.' + rid and
            str(record.get('zenodo_url') or '').rstrip('/') == 'https://zenodo.org/records/' + rid and
            isinstance(record.get('title'), str) and bool(_text(record['title'])) and
            isinstance(record.get('accession'), str) and bool(_text(record['accession'])))


# Descriptive alias for callers that use the feed independently of build.py.
publication_eligible = public_export_eligible


def load_source_snapshots(records, source_directory):
    """Read numeric-ID snapshots only, without following paths from metadata.

    Missing, malformed or escaping symlink snapshots are left out, making those
    records ineligible. The caller can compare result IDs with the public feed to
    report omissions. No network request, source mutation or import-time I/O.
    """
    root = Path(source_directory).resolve()
    snapshots = {}
    for record in records:
        rid = str(record.get('id') or '')
        if not re.fullmatch(r'[1-9][0-9]*', rid):
            continue
        path = (root / (rid + '.json')).resolve()
        if path.parent != root:
            continue
        try:
            source = json.loads(path.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            continue
        if isinstance(source, dict):
            snapshots[rid] = source
    return snapshots


def searchable_text(record):
    """Shared catalogue/feed search scope; does not serialize arbitrary metadata."""
    terms = [record.get(key) for key in (
        'title', 'short_title', 'source_title', 'accession', 'author', 'doi',
        'conceptdoi', 'isbn', 'summary', 'type', 'collection',
    )]
    terms += _strings(record.get('subjects')) + _strings(record.get('keywords'))
    creators = record.get('creators') or []
    terms += [creator.get('name') for creator in _objects(creators)] + _strings(creators)
    terms += [title.get('title') for title in _objects(record.get('alternate_titles'))]
    terms += [entity.get('label') for entity in _objects(record.get('entity_links'))]
    terms += [part.get('title') for part in _objects(record.get('contents'))]
    for subject in _objects(record.get('controlled_subjects')):
        terms += _strings(subject.get('alternative_labels'))
    for programme in _objects(record.get('research_programmes')):
        terms += [programme.get('title'), _programme_id(programme)]
    for programme in _objects(record.get('pirr_references')):
        terms += [programme.get('programme_title'), programme.get('programme_key')]
        terms += [identifier.get('value') for identifier in _objects(programme.get('identifiers'))]
    # Retain supplied spelling; normalization stays with the browser matcher.
    return ' '.join(dict.fromkeys(_text(term) for term in terms if _text(term)))


def _programme_id(programme):
    return urlsplit(str(programme.get('url') or '')).path.rstrip('/').split('/')[-1]


def _programme_links(record, origin):
    references = {p.get('programme_key'): p for p in _objects(record.get('pirr_references'))}
    result = []
    for programme in _objects(record.get('research_programmes')):
        pid = _programme_id(programme)
        url = _public_url(programme.get('url'))
        source_url = _public_url(programme.get('source_url'))
        if not pid or not url or not source_url:
            continue  # Do not imply an unsourced publication/programme relation.
        link = {'id': pid, 'title': _text(programme.get('title')), 'url': url,
                'status': _text(programme.get('status')), 'source_url': source_url}
        relation = _text(programme.get('relation_label') or programme.get('relation'))
        if relation:
            link['relation'] = relation
        reference = references.get(pid, {})
        identifiers = []
        for identifier in _objects(reference.get('identifiers')):
            evidence = _public_url(identifier.get('source_url'))
            if evidence:
                identifiers.append({'scheme': _text(identifier.get('scheme')),
                                    'value': _text(identifier.get('value')), 'source_url': evidence})
        if identifiers:
            link['identifiers'] = identifiers
            link['registry_url'] = origin + '/research-registry.html#' + pid
        result.append(link)
    return sorted(result, key=lambda value: value['id'])


def encode_search_index(payload):
    """Canonical, compact JSON; also the exact bytes used for content hashing."""
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def build_search_index(records, origin, source_snapshots):
    """Return a deterministic v1 feed of eligible records from enriched catalogue.

    ``source_snapshots`` is a dictionary keyed by string Zenodo record ID, usually
    produced by load_source_snapshots(). The function does not mutate its inputs.
    Omitted records contribute no text, identifiers or dates to the public feed.
    Duplicate eligible IDs/accessions raise ValueError instead of aliasing URLs.
    """
    origin = _origin(origin)
    entries, ids, accessions = [], set(), set()
    for record in records:
        rid = str(record.get('id') or '')
        if not public_export_eligible(record, source_snapshots.get(rid)):
            continue
        accession = _text(record['accession'])
        if rid in ids or accession in accessions:
            raise ValueError('Duplicate eligible search record ID or accession: ' + rid)
        ids.add(rid)
        accessions.add(accession)
        reviewed = _text(record.get('source_review'))
        sources = [{'role': 'repository', 'url': record['zenodo_url'], 'reviewed': reviewed}]
        if record.get('osf_copy'):
            o = record['osf_copy']
            sources.append({'role': 'verified_exact_edition_copy', 'url': o['osf_url'], 'reviewed': o['verified_at']})
        institution = _public_url(record.get('institutional_url'))
        if institution:
            citation = {'role': 'institutional', 'url': institution}
            institutional = record.get('institutional_metadata') or {}
            if (isinstance(institutional, Mapping) and
                    institution.rstrip('/') == str(institutional.get('source_url') or '').rstrip('/') and
                    _text(institutional.get('reviewed'))):
                citation['reviewed'] = _text(institutional['reviewed'])
            sources.append(citation)
        entry = {
            'id': rid, 'accession': accession, 'url': origin + '/items/' + rid + '.html',
            'title': record['title'], 'author': _text(record.get('author')),
            'date': _text(record.get('date')), 'date_precision': _text(record.get('date_precision')),
            'date_role': 'repository_publication', 'type': _text(record.get('type')),
            'collection': _text(record.get('collection')), 'subjects': _strings(record.get('subjects')),
            'summary': _text(record.get('summary'))[:320], 'doi': _doi(record.get('doi')),
            'programmes': _programme_links(record, origin), 'sources': sources,
            'search_text': searchable_text(record),
        }
        entries.append(entry)
    payload = {'schema_version': SCHEMA_VERSION, 'scope': SCOPE,
               'canonical_origin': origin, 'records': sorted(entries, key=lambda value: value['id'])}
    payload['content_version'] = sha256(encode_search_index(payload).encode('utf-8')).hexdigest()
    return payload
