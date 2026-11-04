"""Attach only public OSF copies proven identical to the selected DOI edition."""
import hashlib
import json
import re
from urllib.parse import urlparse


def attach_osf_editions(records, root):
    path = root / 'data/osf-editions.json'
    if not path.exists():
        return records
    rows = json.loads(path.read_text())
    by_id = {str(r['id']): r for r in records}
    seen = set()
    for row in rows:
        key = row['archive_id']
        if key in seen or key not in by_id:
            raise ValueError('Duplicate or unknown OSF edition mapping: ' + key)
        seen.add(key)
        r = by_id[key]
        reading = r.get('reading_copy') or {}
        if row['public_project'] != 'zhnre' or row['edition_doi'] != r['doi']:
            raise ValueError('OSF project or edition mismatch: ' + key)
        if row['sha256'] != reading.get('sha256') or row['bytes'] != reading.get('bytes'):
            raise ValueError('OSF copy differs from verified reading edition: ' + key)
        pdf = root / 'dist/assets/documents' / (key + '.pdf')
        if hashlib.sha256(pdf.read_bytes()).hexdigest() != row['sha256']:
            raise ValueError('Reading copy changed since OSF verification: ' + key)
        u = urlparse(row['osf_url'])
        if u.scheme != 'https' or u.netloc != 'osf.io' or not re.fullmatch(r'/zhnre/files/[a-z0-9]+', u.path) or u.query or u.fragment:
            raise ValueError('Unexpected public OSF record URL: ' + key)
        d = urlparse(row['osf_download_url'])
        if d.scheme != 'https' or d.netloc != 'osf.io' or not d.path.startswith('/download/'):
            raise ValueError('Unexpected public OSF download URL: ' + key)
        r['osf_copy'] = {k: row[k] for k in ('archive_id', 'edition_doi', 'osf_file_id', 'osf_guid', 'osf_url', 'osf_download_url', 'osf_version', 'sha256', 'bytes', 'verified_at', 'public_project')}
        r.setdefault('field_assertions', []).append({'field': 'osf_copy', 'value': r['osf_copy'], 'source_url': 'https://api.osf.io/v2/files/' + row['osf_file_id'] + '/', 'status': 'derived_file_inspection', 'reviewed': row['verified_at'], 'note': 'Anonymous OSF download SHA-256 and byte count matched the selected DOI edition reading copy. OSF is an access location, not a new edition or rights grant.'})
    return records
