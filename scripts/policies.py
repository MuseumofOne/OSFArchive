"""Public description policy and source-qualified catalogue revision history.

This module adds local descriptive context without changing source metadata.
It makes no assertion of physical acquisition or original archival custody.
"""
from copy import deepcopy
from html import escape
from pathlib import Path
from urllib.parse import urlencode
import json

ROOT = Path(__file__).resolve().parents[1]


def _policy():
    return json.loads((ROOT / 'data/policies.json').read_text())


def _e(value):
    return escape(str(value or ''), quote=True)


def _mailto(subject, body=''):
    values = {'subject': subject}
    if body:
        values['body'] = body
    return 'mailto:' + _policy()['responsible_service']['email'] + '?' + urlencode(values)


def _prior_records(existing_data):
    if isinstance(existing_data, list):
        return {str(r['id']): r for r in existing_data if isinstance(r, dict) and 'id' in r}
    if isinstance(existing_data, dict):
        if 'records' in existing_data:
            return _prior_records(existing_data['records'])
        return {str(k): v for k, v in existing_data.items() if isinstance(v, dict)}
    return {}


def attach_catalogue_history(records, existing_data=None):
    """Return enriched copies, preserving source fields and any earlier events.

    ``existing_data`` may be earlier catalogue records or a mapping keyed by
    record id. Stable event ids make repeated builds idempotent. Reading-copy
    facts come from a record manifest or the documented local file manifest;
    unknown source retrieval and custody information is never fabricated.
    """
    policy = _policy()
    previous = _prior_records(existing_data)
    manifest_path = ROOT / 'data/readers.json'
    manifests = json.loads(manifest_path.read_text()) if manifest_path.exists() else []
    copies = {str(m['id']): m for m in manifests}
    result = []
    for original in records:
        record = deepcopy(original)
        rid = str(record['id'])
        provenance = record.get('provenance') or {}
        source_files = record.get('files') or []
        copy = record.get('reading_copy') or copies.get(rid)
        repository_url = record.get('zenodo_url')
        source_urls = [u for u in (repository_url, record.get('institutional_url')) if u]
        event_base = {
            'responsible_service': policy['responsible_service']['name'],
            'method': 'Source-based automated description assistance',
            'date_kind': 'Catalogue description event; not a publication or acquisition date',
        }
        events = []
        if repository_url:
            events.append(dict(event_base,
                event_id='public-source-description-2026-11-04',
                date=policy['effective_date'],
                action='Source-based catalogue description',
                note='Local description assembled from the identified public repository record and available institutional work record. Source metadata remains separately identifiable.',
                sources=source_urls))
        if provenance.get('editorial_fields') or record.get('metadata_profile') or record.get('date_precision'):
            events.append(dict(event_base,
                event_id='qualified-description-2026-11-04',
                date=policy['effective_date'],
                action='Qualified descriptive enrichment',
                note='Local editorial description, arrangement and source-qualified bibliographic context recorded alongside source metadata. Unknown or disputed values remain qualified.',
                fields=provenance.get('editorial_fields', []), sources=source_urls))
        if copy and copy.get('verified_at') and copy.get('checksum_match') is True:
            events.append(dict(event_base,
                event_id='access-copy-verification-' + copy['verified_at'],
                date=copy['verified_at'],
                action='Digital reading copy verified',
                note='Downloaded access-copy MD5 matched the source checksum; local SHA-256 and PDF file-page count are recorded in the file manifest. This event does not describe transfer of custody.',
                method='Automated file checksum and PDF inspection',
                sources=[copy['source_url']] if copy.get('source_url') else []))
        events.append(dict(event_base,
            event_id='description-policy-1.0-2026-11-04',
            date=policy['effective_date'],
            action='Description policy and provenance context adopted',
            note='Responsible service, source repository, local access-copy role, unknown custody and original order, correction route and dated description history made explicit under ' + policy['profile_id'] + '.',
            sources=['policies.html']))
        history = []
        seen = set()
        for event in (previous.get(rid, {}).get('description_history', [])
                      + record.get('description_history', []) + events):
            key = event.get('event_id') or json.dumps(event, sort_keys=True)
            if key not in seen:
                history.append(deepcopy(event))
                seen.add(key)
        filenames = [f.get('name') for f in source_files if f.get('name')]
        if copy and copy.get('source_filename') and copy['source_filename'] not in filenames:
            filenames.append(copy['source_filename'])
        context = deepcopy(record.get('archival_context') or {})
        context.update({
            'description_profile': policy['profile_id'],
            'catalogue_snapshot_date': policy['catalogue_snapshot_date'],
            'snapshot_note': 'Selected catalogue snapshot; not a live repository synchronisation.',
            'record_category': 'Published library and repository material',
            'reference_code_status': 'Stable local catalogue reference; not evidence of an archival acquisition or a former Omeka accession.',
            'source_repository': {'name': 'Zenodo' if repository_url else 'Not documented', 'record_url': repository_url},
            'institutional_context_url': record.get('institutional_url'),
            'source_metadata_retrieved': provenance.get('retrieved'),
            'source_metadata_retrieval_status': 'Documented in catalogue source provenance' if provenance.get('retrieved') else 'Not documented',
            'source_snapshot': provenance.get('source_snapshot'),
            'source_filenames': filenames,
            'selection_basis': 'Local descriptive selection of publicly published material; public availability does not establish ownership of originals.',
            'custodial_history': {'status': 'not_documented', 'statement': 'No donation, physical transfer, acquisition agreement or chain of custody is documented by this catalogue. Zenodo remains the source repository for the deposited version.'},
            'original_order': {'status': 'not_documented', 'statement': 'No original archival order is asserted. Current browsing groupings are local editorial arrangement.'},
            'arrangement': {'status': 'local_editorial', 'grouping': record.get('collection'), 'statement': 'A browsing grouping, not an original fonds or archival series.'},
            'responsible_service': deepcopy(policy['responsible_service']),
            'description_method': policy['description_method'],
            'policy_url': 'policies.html',
            'correction_email': policy['responsible_service']['email'],
        })
        if copy:
            context['access_copy'] = {
                'role': 'Local digital reading copy of the deposited file',
                'source_url': copy.get('source_url'),
                'source_filename': copy.get('source_filename'),
                'local_path': 'assets/documents/' + rid + '.pdf',
                'verified_at': copy.get('verified_at'),
                'source_checksum_match': copy.get('checksum_match'),
                'sha256': copy.get('sha256'),
                'statement': 'Access copy only; no ownership or physical custody transfer is implied.',
            }
        else:
            context['access_copy'] = {'role': 'No local reading-copy manifest documented'}
        record['description_history'] = history
        record['archival_context'] = context
        result.append(record)
    return result


def policy_record_panel(record, base='../'):
    """Render the added accountability fields on a catalogue item page."""
    context = record.get('archival_context') or {}
    if not context:
        return ''
    code = record.get('accession') or record['id']
    correction = _mailto('Catalogue correction: ' + code,
        'Reference: ' + code + '\nDOI: ' + record.get('doi', '') + '\nField to correct:\nProposed correction:\nSupporting source:\n')
    rows = [
        ('Responsible service', _e(context['responsible_service']['name'])),
        ('Catalogue snapshot', _e(context['catalogue_snapshot_date']) + ' · Selected catalogue, not live synchronisation'),
        ('Source metadata retrieved', _e(context.get('source_metadata_retrieved') or 'Not documented')),
        ('Original source filenames', '<br>'.join(_e(n) for n in context.get('source_filenames', [])) or 'Not documented'),
        ('Selection and custody', _e(context['custodial_history']['statement'])),
        ('Original order', _e(context['original_order']['statement'])),
    ]
    copy = context.get('access_copy') or {}
    if copy.get('verified_at'):
        rows.append(('Access-copy verification', _e(copy['verified_at']) + ' · ' + _e(copy['role'])))
    body = '<section class="item-section" id="description-history"><div class="section-no">Responsibility / Sources / Revision</div><h2>Description history &amp; responsibility</h2><dl class="context-register">'
    body += ''.join('<div><dt>' + _e(k) + '</dt><dd>' + v + '</dd></div>' for k, v in rows) + '</dl>'
    body += '<p>' + _e(context['description_method']) + '</p><ol class="source-list">'
    for event in record.get('description_history', []):
        body += '<li><strong>' + _e(event.get('date')) + ' · ' + _e(event.get('action')) + '</strong><p>' + _e(event.get('note')) + '</p><small>' + _e(event.get('method')) + ' · ' + _e(event.get('responsible_service')) + '</small></li>'
    body += '</ol><p><a href="' + _e(base) + 'policies.html">Read the collecting and description policies ↗</a> · <a href="' + _e(correction) + '">Request a record correction ↗</a></p></section>'
    return body


def build_policy_pages(records, write, layout, origin):
    """Write public policies, research assistance and machine-readable practice."""
    policy = _policy()
    service = policy['responsible_service']
    mail = _mailto('Museum of One archive research enquiry',
        'Research topic:\nRelevant catalogue reference or DOI:\nWhat I need help with:\n')
    correction = _mailto('Museum of One catalogue correction',
        'Catalogue reference or DOI:\nField to correct:\nProposed correction:\nSupporting source:\n')
    content = '<div class="page-head"><div class="breadcrumb"><a href="index.html">Archive</a> / Policies</div><div class="eyebrow">Institutional practice / Description profile 1.0</div><h1>Collecting &amp; description policies</h1><p>How material is selected, described, contextualised and made available.</p></div>'
    content += '<section class="finding-summary"><dl class="context-register"><div><dt>Responsible service</dt><dd>Museum of One Digital Archive Library / Museum of One</dd></div><div><dt>Effective date</dt><dd>' + _e(policy['effective_date']) + '</dd></div><div><dt>Catalogue snapshot</dt><dd>' + _e(policy['catalogue_snapshot_date']) + ' · ' + str(len(records)) + ' selected item descriptions</dd></div><div><dt>Public research contact</dt><dd><a href="mailto:' + _e(service['email']) + '">' + _e(service['email']) + '</a></dd></div><div><dt>Policy status</dt><dd>Operating practice for the current selected catalogue; version ' + _e(policy['version']) + '</dd></div></dl></section>'
    content += '<nav class="record-tabs" aria-label="Policy sections">' + ''.join('<a href="#' + _e(s['id']) + '">' + _e(s['title']) + ' ↓</a>' for s in policy['sections']) + '</nav><div class="finding-text">'
    for section in policy['sections']:
        content += '<section id="' + _e(section['id']) + '"><h2>' + _e(section['title']) + '</h2>' + ''.join('<p>' + _e(p) + '</p>' for p in section['paragraphs']) + '</section>'
    content += '<section><h2>Contact the responsible service</h2><p><a class="button" href="' + _e(mail) + '">Request research assistance ↗</a> <a class="button outline" href="' + _e(correction) + '">Request a correction ↗</a></p><p><a href="research-help.html">Research enquiry guidance ↗</a> · <a href="sources.html">Source register ↗</a> · <a href="finding-aid.html">Finding aid ↗</a> · <a href="metadata/policies.json" download>Download the policy profile · JSON ↓</a></p></section></div>'
    schema = {'@context': 'https://schema.org', '@type': 'WebPage', 'name': 'Collecting and description policies', 'url': origin + '/policies.html', 'dateModified': policy['effective_date'], 'publisher': {'@type': 'Organization', 'name': service['name'], 'url': service['website']}}
    write('policies.html', layout('Collecting & description policies', 'Museum of One collecting scope, description practice, source context, rights and correction process.', content, 'policies.html', schema=schema))
    help_content = '''<div class="page-head"><div class="breadcrumb"><a href="index.html">Archive</a> / Research assistance</div><div class="eyebrow">Reading room / Public research contact</div><h1>Research assistance</h1><p>Ask about a catalogue description, locate a deposited publication or send a documented correction.</p></div><div class="finding-text"><section><h2>Enquiries</h2><p>Museum of One is the responsible service for the Digital Archive Library. The public research contact is <a href="mailto:research@museumofone.art">research@museumofone.art</a>.</p><p>Include your research topic, the relevant local reference code or DOI, and the question you want to resolve. For a correction, identify the field, propose the corrected wording and link to supporting evidence. Please do not send confidential documents or proposed deposits in an initial enquiry.</p><p><a class="button" href="''' + _e(mail) + '''">Write a research enquiry ↗</a> <a class="button outline" href="''' + _e(correction) + '''">Send a catalogue correction ↗</a></p><p>These links open your email application. The archive does not submit a web form, issue an automatic ticket or guarantee a response time.</p></section><section><h2>Before you write</h2><p>The <a href="catalogue.html">item register</a> provides reference codes, descriptions, rights and citations. The <a href="finding-aid.html">finding aid</a> explains the selected corpus and local arrangement. The <a href="sources.html">source register</a> identifies the repository and institutional evidence.</p><p>Published reading copies are available through item records. Rights to reuse a publication or its third-party material must be checked against the source licence and relevant rights holder. An enquiry does not grant permission.</p></section><section><h2>Future records and sensitive material</h2><p>Questions about potential future primary records, rights, personal information or access restrictions should identify the material and the reason for the enquiry. No transfer, donation or consent is established by sending an email. Any future deposit requires a separate documented agreement and access assessment.</p><p><a href="policies.html">Read the collecting and description policies ↗</a></p></section></div>'''
    write('research-help.html', layout('Research assistance', 'Contact Museum of One about catalogue records, research questions, corrections, rights and access.', help_content, 'research-help.html'))
    exported = deepcopy(policy)
    exported['catalogue_record_count'] = len(records)
    exported['description_histories_url'] = origin + '/metadata/description-history.json'
    write('metadata/policies.json', json.dumps(exported, ensure_ascii=False, indent=2))
    write('metadata/description-history.json', json.dumps([
        {'id': r['id'], 'reference': r.get('accession'), 'description_history': r.get('description_history', []), 'archival_context': r.get('archival_context', {})}
        for r in records
    ], ensure_ascii=False, indent=2))
    return ['policies.html', 'research-help.html']
