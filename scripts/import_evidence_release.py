#!/usr/bin/env python3
"""Validate an explicit evidence release; import locally only with --apply.

No network, source discovery, publishing, or rights inference. The manifest is
committed last: readers see the previous complete record until that replacement.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import date, datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import tempfile
from urllib.parse import urlsplit
import uuid

from evidence import FIELDS, prepare_evidence, public_release, safe_url, slug
from image_dimensions import dimensions

GROUPS = tuple(FIELDS) + ('sources', 'claims')
MAX_JSON = 20 * 1024 * 1024
MAX_ASSET = 25 * 1024 * 1024
MAX_TOTAL = 512 * 1024 * 1024
SHA = re.compile(r'[0-9a-f]{64}')
SOURCE_FIELDS = set('id documentId title url recordUrl locator readings verification limitations sourceSHA256 retrievedAtUTC imageReproduced'.split())
CLAIM_FIELDS = set('id title level status text statement support publishedDiscussion sourceIds limitation limitations reopening responsibility'.split())
PRIVATE_KEYS = {'privatenotes', 'auditonly', 'credentials', 'password', 'accesstoken', 'apikey', 'secret', 'localpath', 'sourcepath', 'privatepath'}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode('utf-8')


def record_hash(value):
    """Hash for migration.replaces; insensitive to JSON whitespace/key order."""
    return digest(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode())


def require(condition, message):
    if not condition:
        raise ValueError(message)


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, 'Duplicate JSON key: ' + key)
        result[key] = value
    return result


def read_json(path):
    require(path.is_file() and not path.is_symlink(), 'Expected a regular JSON file: ' + str(path))
    require(path.stat().st_size <= MAX_JSON, 'JSON exceeds the release limit')
    raw = path.read_bytes()
    value = json.loads(raw, object_pairs_hook=unique_object,
                       parse_constant=lambda value: (_ for _ in ()).throw(ValueError('Nonfinite JSON number')))
    require(isinstance(value, dict), 'Expected a JSON object')
    return value, raw


def checked_path(base, relative):
    """Do not resolve a symlink before testing each path component."""
    require(isinstance(relative, str) and relative and '\\' not in relative and '%' not in relative,
            'Invalid release path')
    parts = PurePosixPath(relative).parts
    require(not relative.startswith('/') and all(p not in ('.', '..') for p in relative.split('/')),
            'Absolute paths and traversal are forbidden')
    target = base
    for part in parts:
        target = target / part
        require(not target.is_symlink(), 'Symlinks are forbidden: ' + relative)
    return target


def approval(value, label):
    require(isinstance(value, dict) and public_release(value), label + ' needs explicit publication and privacy approval')
    try:
        date.fromisoformat(value['approvedAt'])
    except (ValueError, TypeError):
        raise ValueError(label + ' has an invalid approval date') from None
    require(isinstance(value['approvedBy'], str) and value['approvedBy'].strip(), label + ' needs a named reviewer')


def scan_public(value):
    """Catch known private payload markers; human review remains mandatory."""
    if isinstance(value, dict):
        for key, item in value.items():
            normalized = re.sub('[^a-z]', '', key.lower())
            require(normalized not in PRIVATE_KEYS, 'Private/audit field is not a public release field: ' + key)
            if normalized in ('private', 'draft', 'hidden'):
                require(item in (False, None), 'Nonpublic record marker: ' + key)
            if normalized == 'visibility':
                require(item == 'public', 'Nonpublic visibility')
            scan_public(item)
    elif isinstance(value, list):
        for item in value:
            scan_public(item)
    elif isinstance(value, str):
        require(not re.search(r'(?:file://|/Users/|/Volumes/|/home/)', value), 'Private filesystem path in public payload')


def image_path(src, origin):
    p = urlsplit(str(src))
    if p.scheme:
        require(p.scheme + '://' + p.netloc == origin, 'Import images must belong to the canonical archive origin')
    else:
        require(str(src).startswith('/') and not p.netloc, 'Image path must be archive-root relative')
    require(not p.query and not p.fragment and p.path.startswith('/assets/rai-archive/'), 'Invalid released image URL')
    path = p.path[1:]
    checked_path(Path('.'), path)
    require(PurePosixPath(path).suffix.lower() in ('.png', '.jpg', '.jpeg', '.webp'), 'Only reviewed PNG/JPEG/WebP derivatives are supported')
    return path


def images(payload, origin):
    found = {}
    for doc in payload.get('documents', []):
        for page in doc.get('pages', []):
            image = page.get('image')
            if image:
                path = image_path(image['src'], origin)
                require(all(type(image.get(k)) is int and image[k] > 0 for k in ('width', 'height')), 'Image dimensions must be positive integers')
                expected = {k: image.get(k) for k in ('sha256', 'width', 'height')}
                require(path not in found or found[path] == expected, 'Conflicting image declarations: ' + path)
                found[path] = expected
    return found


def validate_payload(payload, origin):
    require(set(payload) <= {'schema', 'scope', 'publication', 'release', *GROUPS}, 'Unknown top-level public payload field')
    scan_public(payload)
    approval(payload.get('publication') or payload.get('release'), 'Release')
    for group in GROUPS:
        require(isinstance(payload.get(group, []), list), 'Expected record array: ' + group)
        seen = set()
        allowed = set(FIELDS[group]) | {'recordUrl'} if group in FIELDS else SOURCE_FIELDS if group == 'sources' else CLAIM_FIELDS
        for record in payload.get(group, []):
            require(isinstance(record, dict) and set(record) <= allowed, 'Unknown public fields in ' + group)
            rid = slug(record.get('id'))
            require(rid not in seen, 'Duplicate identifier in ' + group + ': ' + rid)
            seen.add(rid)
            if record.get('publication') or record.get('release'):
                approval(record.get('publication') or record['release'], rid)
    docs = {d['id']: d for d in payload.get('documents', [])}
    sources = {s['id']: s for s in payload.get('sources', [])}
    claims = {c['id']: c for c in payload.get('claims', [])}
    dossiers = {d['id']: d for d in payload.get('dossiers', [])}
    for doc in docs.values():
        provenance = doc.get('provenance')
        require(isinstance(provenance, dict) and provenance, 'Document needs public provenance: ' + doc['id'])
        require(SHA.fullmatch(str(provenance.get('sourceFileSHA256', ''))), 'Document needs a source checksum: ' + doc['id'])
        require(provenance.get('verification') or provenance.get('rendering'), 'Document needs a statement of verification or derivation')
        for key in ('dossierIds', 'dossiers'):
            require(all(r in dossiers for r in doc.get(key, [])), 'Unknown document dossier')
        rights = doc.get('rights', {})
        for page in doc.get('pages', []):
            require(page.get('locator'), 'Each page needs an exact source locator')
            image = page.get('image')
            if image:
                require(image.get('privacyReviewed') is True and image.get('metadataReviewed') is True,
                        'Each image needs visual/privacy and embedded-metadata review')
                require(SHA.fullmatch(str(image.get('sha256', ''))), 'Each image needs a SHA-256 checksum')
            for key in ('transcription', 'translation', 'commentary'):
                layer = page.get(key)
                if not layer:
                    continue
                require(rights.get(key + 'Approved') is True, 'Reading layer lacks permission: ' + key)
                require(layer.get('kind'), 'Reading layer needs an explicit kind')
                for passage in layer.get('passages', []):
                    require(passage.get('text'), 'Selected passage is empty')
                    if passage.get('bbox'):
                        require(passage['bbox'][2] > 0 and passage['bbox'][3] > 0, 'Selected region must have positive area')
    for source in sources.values():
        require(source.get('documentId') in docs and safe_url(source.get('url')), 'Invalid source document or URL')
        require(SHA.fullmatch(str(source.get('sourceSHA256', ''))), 'Source needs a checked-content checksum')
        require(source.get('locator') and source.get('verification') and source.get('retrievedAtUTC'), 'Source needs locator, retrieval date and verification limits')
        try:
            datetime.fromisoformat(source['retrievedAtUTC'].replace('Z', '+00:00'))
        except (ValueError, TypeError):
            raise ValueError('Invalid source retrieval date') from None
    for dossier in dossiers.values():
        require(all(i in sources for i in dossier.get('sourceIds', [])), 'Unknown dossier source')
        require(all(i in claims for i in dossier.get('claimIds', [])), 'Unknown dossier claim')
    for claim in claims.values():
        require(claim.get('text') or claim.get('statement'), 'Claim needs text')
        for ref in claim.get('support', []) + claim.get('publishedDiscussion', []):
            if ref.get('sourceId'):
                require(ref['sourceId'] in sources, 'Unknown claim source reference')
            if ref.get('passageId'):
                doc = docs.get(ref.get('documentId'), {})
                page = next((p for p in doc.get('pages', []) if p['id'] == ref.get('pageId')), {})
                ids = {s['id'] for key in ('transcription', 'translation', 'commentary')
                       for s in (page.get(key) or {}).get('passages', [])}
                require(ref['passageId'] in ids, 'Unknown claim passage reference')
    return prepare_evidence(payload, origin)


def verify_asset(path, expected):
    require(path.is_file() and not path.is_symlink(), 'Missing regular released asset: ' + str(path))
    size = path.stat().st_size
    require(0 < size <= MAX_ASSET, 'Image exceeds release size limit')
    require(SHA.fullmatch(str(expected.get('sha256', ''))), 'Missing or invalid asset checksum')
    require(digest(path.read_bytes()) == expected['sha256'], 'Asset checksum mismatch: ' + path.name)
    if 'bytes' in expected:
        require(type(expected['bytes']) is int and size == expected['bytes'], 'Asset size mismatch')
    dimensions.cache_clear()
    require(dimensions(str(path)) == (expected.get('width'), expected.get('height')), 'Asset dimension mismatch: ' + path.name)
    return size


def merge_records(existing, incoming, manifest, allow_migration, old_hash):
    if existing is None:
        return deepcopy(incoming), []
    result = deepcopy(existing)
    changed = []
    for group in GROUPS:
        if group not in existing and group not in incoming:
            continue
        records = {r['id']: r for r in result.get(group, [])}
        for record in incoming.get(group, []):
            old = records.get(record['id'])
            if old is not None and old != record:
                changed.append((group, record['id'], old, record))
            records[record['id']] = deepcopy(record)
        result[group] = list(records.values())
    if changed:
        migration = manifest.get('migration', {})
        require(allow_migration, 'Existing record differs; an explicit reviewed migration is required')
        approval(migration, 'Migration')
        require(migration.get('reason') and migration.get('expectedExistingSha256') == old_hash, 'Migration reason or baseline checksum is missing/stale')
        replacements = migration.get('replaces', [])
        approved = {(r['group'], r['id']): r['expectedSha256'] for r in replacements}
        require(len(approved) == len(replacements) and set(approved) == {(g, i) for g, i, _, _ in changed}, 'Migration must name exactly the changed records')
        for group, rid, old, new in changed:
            require(approved[(group, rid)] == record_hash(old), 'Migration record baseline mismatch: ' + rid)
            if group == 'documents':
                require(new.get('firstReleased') == old.get('firstReleased'), 'First-release date must be retained')
                old_pages = {p['id'] for p in old.get('pages', [])}
                require(old_pages <= {p['id'] for p in new.get('pages', [])}, 'Existing page identities cannot be removed')
                next_pages = {p['id']: p for p in new.get('pages', [])}
                for page in old.get('pages', []):
                    for layer in ('transcription', 'translation', 'commentary'):
                        old_ids = {p['id'] for p in (page.get(layer) or {}).get('passages', [])}
                        next_ids = {p['id'] for p in (next_pages[page['id']].get(layer) or {}).get('passages', [])}
                        require(old_ids <= next_ids, 'Existing passage identities cannot be removed')
                old_revisions = old.get('revisions', [])
                revisions = new.get('revisions', [])
                require(revisions[:len(old_revisions)] == old_revisions and len(revisions) > len(old_revisions), 'Migration must retain and extend record history')
                last = revisions[-1]
                require(last.get('date') == migration['approvedAt'] and last.get('by') and last.get('description'), 'Migration needs a dated, attributed revision note')
    result.pop('release', None)
    result['publication'] = deepcopy(incoming.get('publication') or incoming['release'])
    # A partial import cannot silently replace the overall collection scope.
    if 'scope' not in result and 'scope' in incoming:
        result['scope'] = incoming['scope']
    return result, [{'group': g, 'id': i} for g, i, _, _ in changed]


def plan_release(release_dir, root, origin, allow_migration=False):
    release_dir, root = Path(release_dir).absolute(), Path(root).absolute()
    require(release_dir.is_dir() and root.is_dir(), 'Select existing release and archive folders')
    for path in (root, release_dir):
        require(not path.is_symlink() and not any(p.is_symlink() for p in path.parents), 'Root folders cannot traverse symlinks')
    root, release_dir = root.resolve(), release_dir.resolve()
    require(not release_dir.is_relative_to(root), 'Release folder must stay outside the public repository')
    origin = origin.rstrip('/')
    parsed = urlsplit(origin)
    require(safe_url(origin) and not parsed.path and not parsed.query and not parsed.fragment, 'Origin must be an HTTPS origin only')
    manifest, _ = read_json(checked_path(release_dir, 'release.json'))
    require(set(manifest) <= {'schema', 'evidenceFile', 'evidenceSha256', 'assets', 'migration'}, 'Unknown release manifest field')
    require(manifest.get('schema') == 1 and manifest.get('evidenceFile') == 'evidence.json', 'Unsupported release manifest')
    incoming, incoming_bytes = read_json(checked_path(release_dir, 'evidence.json'))
    require(set(incoming) <= {'schema', 'scope', 'publication', 'release', *GROUPS}, 'Unknown top-level public payload field')
    scan_public(incoming)
    require(digest(incoming_bytes) == manifest.get('evidenceSha256'), 'Evidence checksum mismatch')
    declared = {}
    require(isinstance(manifest.get('assets'), list) and len(manifest['assets']) <= 200, 'Asset list missing or excessive')
    for asset in manifest['assets']:
        require(set(asset) == {'path', 'sha256', 'bytes', 'width', 'height'}, 'Asset manifest fields are incomplete or unknown')
        path = asset['path']
        require(image_path('/' + path, origin) == path and path not in declared, 'Invalid/duplicate asset manifest path')
        require(all(type(asset[k]) is int and asset[k] > 0 for k in ('bytes', 'width', 'height')), 'Asset sizes must be positive integers')
        declared[path] = asset
    allowed = {'release.json', 'evidence.json', *declared}
    for path in release_dir.rglob('*'):
        require(not path.is_symlink(), 'Symlink in release package')
        if path.is_file():
            require(path.relative_to(release_dir).as_posix() in allowed, 'Unlisted/private file in release package: ' + path.name)
        else:
            require(path.is_dir(), 'Special files are not allowed')
    refs = images(incoming, origin)
    require(set(refs) == set(declared), 'Manifest assets must exactly match the incoming image references')
    total = 0
    for path, asset in declared.items():
        require(all(refs[path][key] == asset[key] for key in refs[path]), 'Metadata/manifest image disagreement')
        total += verify_asset(checked_path(release_dir, path), asset)
    require(total <= MAX_TOTAL, 'Release exceeds total asset limit')
    data_path = checked_path(root, 'data/evidence.json')
    existing, old_bytes = read_json(data_path) if data_path.exists() else (None, None)
    merged, changed = merge_records(existing, incoming, manifest, allow_migration, digest(old_bytes) if old_bytes is not None else None)
    validate_payload(merged, origin)
    new_assets = []
    for path, expected in images(merged, origin).items():
        current = checked_path(root, path)
        if current.exists():
            verify_asset(current, expected)
            if path in declared:
                require(digest(current.read_bytes()) == declared[path]['sha256'], 'Never overwrite an existing image; use a new versioned filename')
        else:
            require(path in declared, 'Existing record has an unavailable asset: ' + path)
            new_assets.append(path)
    return dict(root=root, release_dir=release_dir, origin=origin, manifest=manifest,
                merged=merged, old_bytes=old_bytes, new_bytes=encoded(merged), assets=declared,
                new_assets=new_assets, changed=changed,
                report={'status': 'validated-dry-run', 'changedRecords': changed, 'newAssets': new_assets,
                        'recordCounts': {g: len(merged.get(g, [])) for g in GROUPS},
                        'previousSha256': digest(old_bytes) if old_bytes is not None else None,
                        'resultSha256': digest(encoded(merged)), 'publishes': False})


def fsync_write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())


def apply_plan(plan, backup_dir):
    root = plan['root']
    backup_dir = Path(backup_dir).absolute()
    require(not backup_dir.is_symlink() and not any(p.is_symlink() for p in backup_dir.parents), 'Backup location cannot traverse symlinks')
    backup_dir = backup_dir.resolve()
    require(not backup_dir.is_relative_to(root) and not root.is_relative_to(backup_dir), 'Choose a separate private backup folder outside the public repository')
    require(not backup_dir.is_relative_to(plan['release_dir']), 'Backup must be outside the release package')
    lock = root / '.evidence-import.lock'
    descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    installed = []
    committed = False
    backup = None
    try:
        os.write(descriptor, str(os.getpid()).encode())
        target = checked_path(root, 'data/evidence.json')
        current = target.read_bytes() if target.exists() else None
        require(current == plan['old_bytes'], 'Archive record changed since validation; run a fresh dry-run')
        backup_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        backup = backup_dir / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex[:8])
        backup.mkdir(mode=0o700)
        if current is not None:
            fsync_write(backup / 'evidence-before.json', current)
        fsync_write(backup / 'release-manifest.json', encoded(plan['manifest']))
        fsync_write(backup / 'receipt.json', encoded(plan['report']))
        # Retain exact prior referenced images; this directory never enters the repo.
        for path in images(json.loads(current), plan['origin']) if current else []:
            fsync_write(backup / path, checked_path(root, path).read_bytes())
        with tempfile.TemporaryDirectory(prefix='.evidence-import-', dir=root) as folder:
            stage = Path(folder)
            for path in plan['new_assets']:
                source = checked_path(plan['release_dir'], path)
                verify_asset(source, plan['assets'][path])
                fsync_write(stage / path, source.read_bytes())
                verify_asset(stage / path, plan['assets'][path])
            fsync_write(stage / 'evidence.json', plan['new_bytes'])
            # Existing assets are immutable. Recheck them and the metadata.
            for path, expected in images(plan['merged'], plan['origin']).items():
                if path not in plan['new_assets']:
                    verify_asset(checked_path(root, path), expected)
            require((target.read_bytes() if target.exists() else None) == current, 'Concurrent metadata change detected')
            for path in plan['new_assets']:
                destination = checked_path(root, path)
                destination.parent.mkdir(parents=True, exist_ok=True)
                # Exclusive link prevents a race from overwriting an existing path.
                os.link(stage / path, destination)
                installed.append(destination)
            target.parent.mkdir(parents=True, exist_ok=True)
            os.replace(stage / 'evidence.json', target)
            committed = True
        report = dict(plan['report'], status='imported-locally', backup=str(backup))
        # The metadata commit is complete even if recording the receipt fails.
        try:
            (backup / 'receipt.json').write_bytes(encoded(report))
        except OSError:
            report['receiptWarning'] = 'Import committed; backup receipt could not be updated.'
        return report
    finally:
        if not committed:
            for path in reversed(installed):
                path.unlink(missing_ok=True)
        os.close(descriptor)
        lock.unlink(missing_ok=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('release_dir', type=Path)
    parser.add_argument('--root', type=Path, required=True, help='Explicit verified archive project root')
    parser.add_argument('--origin', default='https://archive.museumofone.art')
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--apply', action='store_true', help='Import locally; never builds, pushes or publishes')
    mode.add_argument('--dry-run', action='store_true', help='Validate only (the default)')
    parser.add_argument('--backup-dir', type=Path, help='Required with --apply; outside the public repository')
    parser.add_argument('--allow-reviewed-migration', action='store_true', help='Also requires exact reviewed migration metadata')
    args = parser.parse_args(argv)
    try:
        require(not args.apply or args.backup_dir is not None, '--apply requires a private --backup-dir')
        plan = plan_release(args.release_dir, args.root, args.origin, args.allow_reviewed_migration)
        report = apply_plan(plan, args.backup_dir) if args.apply else plan['report']
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(2, 'Evidence import stopped: ' + str(error) + '\n')


if __name__ == '__main__':
    raise SystemExit(main())
