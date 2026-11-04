"""Versioned source-profile, graph, citation-export and quality validation.

No registry lookups, timestamps invented from the clock, or source mutations.
Builds fail on structural contradictions; documented uncertainty is reported.
"""
from collections import Counter, defaultdict
from copy import deepcopy
from datetime import date
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from urllib.parse import urlsplit
from identities import (DEFAULT_ORIGIN, catalogue_uri, doi_uri, entity_uri, work_uri,
                        institutional_scope, institutional_target, edition_isbn)
from relationship_assertions import typed_relationship_assertions, typed_entity_relationship_assertions, relation_register

ROOT = Path(__file__).resolve().parents[1]
PROFILE = json.loads((ROOT / 'data/metadata-profile.json').read_text())


def prepare_metadata_records(records, origin=DEFAULT_ORIGIN):
    """Call after enrichment/history/entities/contents/vocabulary/PIRR attachment."""
    result = deepcopy(records)
    event_path = ROOT / 'data/description-events.json'
    events = json.loads(event_path.read_text()).get('events', []) if event_path.exists() else []
    authority_path = ROOT / 'data/authorities.json'
    author_identifier = (json.loads(authority_path.read_text()).get('author', {}).get('identifier', {})
                         if authority_path.exists() else {})
    for record in result:
        record['metadata_origin'] = origin.rstrip('/')
        record['metadata_profile'] = {'name': PROFILE['title'], 'version': PROFILE['version'],
                                      'url': origin.rstrip('/') + '/metadata/metadata-profile.json',
                                      'source_snapshot_preserved': True}
        record['identity'] = {'work': work_uri(record, origin), 'edition': doi_uri(record['doi']),
                              'version_family': doi_uri(record.get('conceptdoi')) or None,
                              'catalogue_record': catalogue_uri(record, origin)}
        record['institutional_match_scope'] = institutional_scope(record)
        record['relationship_assertions'] = typed_relationship_assertions(record, origin)
        if str(record.get('orcid', '')).removeprefix('https://orcid.org/') == author_identifier.get('value'):
            record['orcid_authority'] = deepcopy(author_identifier)
        history = record.setdefault('description_history', [])
        for event in events:
            if str(record['id']) in event.get('record_ids', []) and not any(e.get('event_id') == event['event_id'] for e in history):
                history.append({key: deepcopy(value) for key, value in event.items() if key != 'record_ids'})
        valid_days = [e['date'] for e in history if _valid_day(e.get('date'))]
        if valid_days and (not record.get('record_modified') or (record.get('record_modified_provenance') or {}).get('status') == 'derived_from_description_history'):
            record['record_modified'] = max(valid_days)
            record['record_modified_provenance'] = {
                'status': 'derived_from_description_history',
                'event_ids': [e['event_id'] for e in history if e.get('date') == record['record_modified'] and e.get('event_id')],
                'note': 'Latest documented local description event; not a publication, repository or source-review date.',
            }
    return result


def _valid_day(value):
    try:
        return isinstance(value, str) and len(value) == 10 and date.fromisoformat(value).isoformat() == value
    except ValueError:
        return False


def _valid_date(value):
    if not isinstance(value, str) or not re.fullmatch(r'\d{4}(?:-\d{2}){0,2}', value):
        return False
    parts = [int(x) for x in value.split('-')]
    try:
        date(parts[0], parts[1] if len(parts) > 1 else 1, parts[2] if len(parts) > 2 else 1)
        return True
    except ValueError:
        return False


def _http(value):
    return isinstance(value, str) and urlsplit(value).scheme in {'http', 'https'} and bool(urlsplit(value).netloc)


def validate_metadata_profile(records, origin=DEFAULT_ORIGIN):
    """Return error strings; unknown optional facts do not fail completeness."""
    errors = []
    for key in ('id', 'accession', 'doi'):
        values = [str(r.get(key, '')) for r in records]
        duplicates = [value for value, count in Counter(values).items() if count > 1]
        if duplicates:
            errors.append('Duplicate ' + key + ': ' + ', '.join(duplicates))
    kinds = {'string': str, 'array': list, 'object': dict}
    for record in records:
        prefix = str(record.get('id', '<missing>')) + ': '
        for key in PROFILE['required']:
            if record.get(key) in (None, '', [], {}):
                errors.append(prefix + 'missing required field ' + key)
        for key, rule in PROFILE['properties'].items():
            if key not in record:
                continue
            value = record[key]
            if rule.get('type') and not isinstance(value, kinds[rule['type']]):
                errors.append(prefix + key + ' has wrong type')
                continue
            if 'enum' in rule and value not in rule['enum']:
                errors.append(prefix + 'unsupported ' + key + ': ' + str(value))
            if rule.get('pattern') and not re.fullmatch(rule['pattern'], value):
                errors.append(prefix + 'invalid ' + key)
            if rule.get('minLength') and len(value) < rule['minLength']:
                errors.append(prefix + key + ' is empty')
            if rule.get('minItems') and len(value) < rule['minItems']:
                errors.append(prefix + key + ' has no entries')
            if rule.get('format') == 'uri' and not _http(value):
                errors.append(prefix + key + ' is not an HTTP(S) URI')
        if not _valid_date(record.get('date')):
            errors.append(prefix + 'invalid or fabricated publication date')
        if record.get('institutional_match_scope') not in (None, institutional_scope(record)):
            errors.append(prefix + 'institutional match scope exceeds recorded evidence')
        if record.get('record_created') and not record.get('record_created_provenance'):
            errors.append(prefix + 'local creation date lacks provenance')
        try:
            assertions = typed_relationship_assertions(record, origin)
        except (KeyError, ValueError) as exc:
            errors.append(prefix + str(exc))
            continue
        for assertion in assertions:
            if not _http(assertion['source_url']):
                errors.append(prefix + 'relationship has no usable evidence URI')
            if assertion['scope'] not in {'work', 'exact_edition', 'version_family'}:
                errors.append(prefix + 'unsupported relationship scope')
            if assertion.get('reviewed') and not _valid_day(assertion['reviewed']):
                errors.append(prefix + 'invalid relationship review date')
            location = assertion.get('source_location') or {}
            if location.get('kind') == 'pdf_page':
                pages = location.get('pages', [])
                extent = (record.get('reading_copy') or {}).get('page_count')
                if not pages or not extent or any(not isinstance(p, int) or p < 1 or p > extent for p in pages):
                    errors.append(prefix + 'PDF relationship locator falls outside the verified reading copy')
        if 'relationship_assertions' in record and record['relationship_assertions'] != assertions:
            errors.append(prefix + 'cached relationship assertions differ from their evidence inputs')
    return errors


def _objects(value):
    if isinstance(value, dict):
        yield value
        for nested in value.values():
            yield from _objects(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from _objects(nested)


def validate_global_graph(graphs, entity_nodes=None, origin=DEFAULT_ORIGIN):
    """Validate cross-document references, including IDs HTML checks cannot see.

    Supply all item, component and vocabulary graphs plus entity_graph(...).
    Local vocabulary predicate IRIs are validated against the relation register.
    External references need not be locally redeclared.
    """
    all_graphs = list(graphs.values()) if isinstance(graphs, dict) else list(graphs)
    if entity_nodes:
        all_graphs.append(entity_nodes)
    objects = list(_objects(all_graphs))
    definitions = defaultdict(list)
    for node in objects:
        if node.get('@id') and any(key not in {'@id', '@context'} for key in node):
            definitions[node['@id']].append(node)
    predicates = {r['uri'] for r in relation_register(origin)['relations']}
    errors = set()
    for node in objects:
        identity = node.get('@id', '')
        if identity.startswith(origin.rstrip('/') + '/') and identity not in definitions and identity not in predicates:
            errors.add('Undeclared local graph identity: ' + identity)
    for identity, nodes in definitions.items():
        types = set()
        for node in nodes:
            value = node.get('@type', [])
            types.update(value if isinstance(value, list) else [value])
        if 'Person' in types and types & {'Organization', 'Book', 'Dataset', 'ExhibitionEvent', 'CreativeWork'}:
            errors.add('Contradictory entity types at ' + identity + ': ' + ', '.join(sorted(types)))
        if '/entities/' in identity and not identity.endswith('#entity'):
            errors.add('Contextual entity does not use its registered identity: ' + identity)
    return sorted(errors)


def combine_graphs(graphs):
    """Deterministically combine node projections without dropping statements."""
    merged = {}
    contexts = ['https://schema.org']
    for graph in graphs:
        context = graph.get('@context')
        for entry in (context if isinstance(context, list) else [context]):
            if entry and entry not in contexts:
                contexts.append(deepcopy(entry))
        nodes = graph.get('@graph', [graph])
        for node in nodes:
            if not isinstance(node, dict) or not node.get('@id'):
                continue
            target = merged.setdefault(node['@id'], {'@id': node['@id']})
            for key, value in node.items():
                if key in {'@id', '@context'}:
                    continue
                if key not in target:
                    target[key] = deepcopy(value)
                elif target[key] != value:
                    previous = target[key] if isinstance(target[key], list) else [target[key]]
                    incoming = value if isinstance(value, list) else [value]
                    for entry in incoming:
                        if entry not in previous:
                            previous.append(deepcopy(entry))
                    target[key] = previous
    return {'@context': contexts[0] if len(contexts) == 1 else contexts,
            '@graph': [merged[key] for key in sorted(merged)]}


class _Meta(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.tags = defaultdict(list)
        self.feed(text)
    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag == 'meta' and values.get('name', '').startswith('citation_'):
            self.tags[values['name']].append(values.get('content', ''))


def validate_export_agreement(records, output_dir, origin=DEFAULT_ORIGIN):
    """Check on-disk exports after the builder writes them; never rewrite output."""
    from citations import build_citation_model, csl_json, bibtex, ris, scholar_meta
    errors = []
    out = Path(output_dir)
    for record in records:
        rid = str(record['id'])
        pdf = origin.rstrip('/') + '/items/' + rid + '.pdf' if record.get('reading_copy') else None
        model = build_citation_model(record, catalogue_url=origin.rstrip('/') + '/items/' + rid + '.html', pdf_url=pdf)
        expected = {'.csl.json': json.dumps(csl_json(model), sort_keys=True, ensure_ascii=False), '.bib': bibtex(model).strip(), '.ris': ris(model).strip()}
        for suffix, value in expected.items():
            path = out / 'metadata' / (rid + suffix)
            if not path.exists():
                errors.append(rid + ': missing citation export ' + suffix)
                continue
            try:
                actual = json.dumps(json.loads(path.read_text()), sort_keys=True, ensure_ascii=False) if suffix == '.csl.json' else path.read_text().strip()
                if actual != value:
                    errors.append(rid + ': citation export disagrees with shared model: ' + suffix)
            except ValueError:
                errors.append(rid + ': invalid citation JSON')
        path = out / 'items' / (rid + '.html')
        if path.exists():
            actual = dict(_Meta(path.read_text()).tags)
            expected_tags = defaultdict(list)
            for name, value in scholar_meta(model):
                expected_tags[name].append(value)
            if actual != dict(expected_tags):
                errors.append(rid + ': Scholar tags disagree with the citation model')
        else:
            errors.append(rid + ': missing item page for citation validation')
        graph_path = out / 'metadata' / (rid + '.jsonld')
        if graph_path.exists():
            graph = json.loads(graph_path.read_text())
            nodes = {n['@id']: n for n in graph.get('@graph', []) if n.get('@id')}
            edition = nodes.get(doi_uri(record['doi']), {})
            if edition.get('name') != model['title'] or edition.get('datePublished') != model['date']:
                errors.append(rid + ': edition title/date differs between citations and graph')
            if edition.get('isbn') != edition_isbn(record):
                errors.append(rid + ': edition ISBN exceeds evidence scope')
            institutional = nodes.get(record.get('institutional_url'), {})
            if institutional.get('about', {}).get('@id') != institutional_target(record, origin):
                errors.append(rid + ': institutional graph target exceeds evidence scope')
        else:
            errors.append(rid + ': missing edition graph for citation validation')
    return errors


def build_quality_report(records, graphs=(), entity_nodes=None, origin=DEFAULT_ORIGIN, output_dir=None, entity_records=None):
    """A dimensional report, deliberately not a claim of flawless metadata."""
    profile_errors = validate_metadata_profile(records, origin)
    graph_errors = validate_global_graph(graphs, entity_nodes, origin) if graphs else []
    export_errors = validate_export_agreement(records, output_dir, origin) if output_dir else []
    assertions = [a for record in records for a in typed_relationship_assertions(record, origin)]
    if entity_records:
        assertions.extend(typed_entity_relationship_assertions(entity_records, origin))
    return {
        'profile_version': PROFILE['version'], 'scope': 'Local source/profile and generated-output validation. No live registry or indexing verification.',
        'records': len(records), 'passed': not (profile_errors or graph_errors or export_errors),
        'checks': {'profile': {'errors': profile_errors},
                   'global_graph': {'executed': bool(graphs), 'errors': graph_errors},
                   'citation_exports': {'executed': output_dir is not None, 'errors': export_errors}},
        'dimensions': {
            'institutional_match_scope': dict(Counter(institutional_scope(r) for r in records)),
            'typed_relationships': len(assertions),
            'relationships_with_evidence': sum(bool(a['source_url']) for a in assertions),
            'relationships_with_review_date': sum(bool(a['reviewed']) for a in assertions),
            'relationships_with_named_reviewer': sum(bool(a['reviewer']) for a in assertions),
            'relationships_with_passage_locator': sum(a['source_location'].get('kind') == 'pdf_page' for a in assertions),
            'title_level_isbn_format_unresolved': [r['id'] for r in records if r.get('isbn') and not edition_isbn(r)],
            'local_creation_date_unknown': [r['id'] for r in records if not r.get('record_created')],
        },
        'interpretation': 'Unknown or qualified values remain explicit. Structural success does not establish external authority assignment, factual certainty, or search-engine inclusion.',
    }


def require_valid_report(report):
    errors = [error for check in report['checks'].values() for error in check.get('errors', [])]
    if errors:
        raise ValueError('Metadata validation failed:\n' + '\n'.join(errors))
    return report
