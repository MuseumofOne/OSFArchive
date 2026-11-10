"""No-network release tests: preservation, permission gates and rollback."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch
import zlib

SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'
sys.path.insert(0, str(SCRIPTS))
import import_evidence_release as release

ORIGIN = 'https://archive.museumofone.art'
APPROVAL = dict(approved=True, approvedBy='Test reviewer', approvedAt='2026-11-10', privacyReviewed=True)


def png():
    def chunk(kind, data):
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data) & 0xffffffff)
    return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', 1, 1, 8, 2, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(b'\x00\xff\xff\xff')) + chunk(b'IEND', b'')


class EvidenceImportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name).resolve()
        self.root, self.package, self.backups = base / 'archive', base / 'release', base / 'private-backups'
        self.root.mkdir(); self.package.mkdir()
        self.asset = png()
        self.imagepath = 'assets/rai-archive/paper-v1-p01.png'
        self.payload = {'schema': 1, 'publication': deepcopy(APPROVAL), 'scope': 'A reviewed selection.',
            'collections': [{'id': 'collection', 'title': 'Research documents'}],
            'documents': [{'id': 'paper-v1', 'title': 'Published research', 'collectionId': 'collection',
                'sourceUrl': 'https://example.org/paper.pdf', 'sourceLayer': 'research-document',
                'materialType': 'published-paper', 'firstReleased': '2026-11-10', 'revisions': [],
                'provenance': {'sourceFileSHA256': 'a' * 64, 'rendering': 'Unaltered selected page of the author-owned edition.'},
                'rights': {'metadataApproved': True, 'imagesApproved': True, 'transcriptionApproved': True, 'statement': 'Author-owned; approved for release.'},
                'pages': [{'id': 'p01', 'label': 'PDF file page 1', 'locator': 'Published PDF file page 1 of 1',
                    'image': {'src': '/' + self.imagepath, 'width': 1, 'height': 1, 'sha256': release.digest(self.asset), 'alt': 'Test page', 'privacyReviewed': True, 'metadataReviewed': True},
                    'transcription': {'kind': 'extracted-text', 'text': 'Published text.', 'by': 'Test reviewer', 'status': 'Checked extraction', 'passages': []},
                    'translation': None, 'commentary': None}]}]}
        path = self.package / self.imagepath
        path.parent.mkdir(parents=True); path.write_bytes(self.asset)
        self.write_package()

    def tearDown(self):
        self.tmp.cleanup()

    def write_package(self, migration=None):
        content = release.encoded(self.payload)
        (self.package / 'evidence.json').write_bytes(content)
        self.manifest = {'schema': 1, 'evidenceFile': 'evidence.json', 'evidenceSha256': release.digest(content),
            'assets': [{'path': self.imagepath, 'sha256': release.digest(self.asset), 'bytes': len(self.asset), 'width': 1, 'height': 1}]}
        if migration:
            self.manifest['migration'] = migration
        (self.package / 'release.json').write_bytes(release.encoded(self.manifest))

    def plan(self, allow=False):
        return release.plan_release(self.package, self.root, ORIGIN, allow)

    def import_first(self):
        return release.apply_plan(self.plan(), self.backups)

    def test_dry_run_has_no_filesystem_changes(self):
        plan = self.plan()
        self.assertEqual(plan['report']['status'], 'validated-dry-run')
        self.assertEqual(list(self.root.iterdir()), [])
        self.assertFalse(self.backups.exists())
        self.assertEqual(plan['new_assets'], [self.imagepath])

    def test_apply_and_idempotent_repeat_preserve_asset(self):
        report = self.import_first()
        self.assertEqual(report['status'], 'imported-locally')
        metadata = (self.root / 'data/evidence.json').read_bytes()
        again = release.apply_plan(self.plan(), self.backups)
        self.assertEqual((Path(again['backup']) / 'evidence-before.json').read_bytes(), metadata)
        self.assertEqual((Path(again['backup']) / self.imagepath).read_bytes(), self.asset)
        self.assertEqual((self.root / self.imagepath).read_bytes(), self.asset)
        self.assertEqual((self.root / 'data/evidence.json').read_bytes(), metadata)
        self.assertFalse((self.root / '.evidence-import.lock').exists())

    def test_wrong_hash_and_dimension_rejected(self):
        (self.package / self.imagepath).write_bytes(self.asset + b'changed')
        with self.assertRaisesRegex(ValueError, 'checksum mismatch'):
            self.plan()
        (self.package / self.imagepath).write_bytes(self.asset)
        self.payload['documents'][0]['pages'][0]['image']['width'] = 2
        self.write_package()
        self.manifest['assets'][0]['width'] = 2
        (self.package / 'release.json').write_bytes(release.encoded(self.manifest))
        with self.assertRaisesRegex(ValueError, 'dimension mismatch'):
            self.plan()

    def test_unlisted_private_file_and_private_field_rejected(self):
        private = self.package / 'private-notes.txt'; private.write_text('Do not release')
        with self.assertRaisesRegex(ValueError, 'Unlisted/private file'):
            self.plan()
        private.unlink()
        self.payload['documents'][0]['provenance']['privateNotes'] = 'Do not release'
        self.write_package()
        with self.assertRaisesRegex(ValueError, 'Private/audit field'):
            self.plan()

    def test_traversal_and_symlink_rejected(self):
        self.payload['documents'][0]['pages'][0]['image']['src'] = '/assets/rai-archive/../../private.png'
        self.write_package()
        with self.assertRaisesRegex(ValueError, 'traversal'):
            self.plan()
        self.payload['documents'][0]['pages'][0]['image']['src'] = '/' + self.imagepath
        self.write_package()
        file = self.package / self.imagepath; file.unlink()
        other = self.root / 'other.png'; other.write_bytes(self.asset)
        file.symlink_to(other)
        with self.assertRaisesRegex(ValueError, 'Symlink'):
            self.plan()

    def test_permissions_and_unapproved_translation_rejected(self):
        doc = self.payload['documents'][0]
        doc['rights']['imagesApproved'] = False; self.write_package()
        with self.assertRaisesRegex(ValueError, 'release permission'):
            self.plan()
        doc['rights']['imagesApproved'] = True
        doc['pages'][0]['translation'] = {'kind': 'translation', 'by': 'Reviewer', 'status': 'Draft', 'text': 'Another language.'}
        self.write_package()
        with self.assertRaisesRegex(ValueError, 'lacks permission'):
            self.plan()

    def test_unknown_claim_reference_rejected(self):
        self.payload['claims'] = [{'id': 'claim', 'text': 'A bounded finding.', 'support': [{'documentId': 'missing', 'pageId': 'p01'}]}]
        self.write_package()
        with self.assertRaisesRegex(ValueError, 'unavailable evidence'):
            self.plan()

    def test_collision_needs_exact_reviewed_migration_and_history(self):
        self.import_first()
        oldbytes = (self.root / 'data/evidence.json').read_bytes()
        olddoc = json.loads(oldbytes)['documents'][0]
        self.payload['documents'][0]['description'] = 'A corrected public description.'
        self.write_package()
        with self.assertRaisesRegex(ValueError, 'reviewed migration'):
            self.plan()
        migration = dict(APPROVAL, reason='Correct the public description without changing the edition.', expectedExistingSha256=release.digest(oldbytes),
                         replaces=[{'group': 'documents', 'id': 'paper-v1', 'expectedSha256': release.record_hash(olddoc)}])
        self.write_package(migration)
        with self.assertRaisesRegex(ValueError, 'extend record history'):
            self.plan(True)
        self.payload['documents'][0]['revisions'].append({'date': '2026-11-10', 'by': 'Test reviewer', 'description': migration['reason']})
        self.write_package(migration)
        plan = self.plan(True)
        report = release.apply_plan(plan, self.backups)
        self.assertEqual((Path(report['backup']) / 'evidence-before.json').read_bytes(), oldbytes)
        self.assertEqual(json.loads((self.root / 'data/evidence.json').read_text())['documents'][0]['firstReleased'], '2026-11-10')

    def test_existing_asset_cannot_be_replaced(self):
        self.import_first()
        (self.root / self.imagepath).write_bytes(self.asset + b'altered')
        with self.assertRaisesRegex(ValueError, 'checksum mismatch'):
            self.plan()

    def test_failed_commit_removes_only_new_assets(self):
        plan = self.plan()
        with patch.object(release.os, 'replace', side_effect=OSError('simulated commit failure')):
            with self.assertRaisesRegex(OSError, 'simulated'):
                release.apply_plan(plan, self.backups)
        self.assertFalse((self.root / 'data/evidence.json').exists())
        self.assertFalse((self.root / self.imagepath).exists())
        self.assertFalse((self.root / '.evidence-import.lock').exists())
        self.assertEqual(len(list(self.backups.iterdir())), 1)

    def test_concurrent_record_change_stops_apply(self):
        self.import_first()
        plan = self.plan()
        target = self.root / 'data/evidence.json'
        newbytes = target.read_bytes() + b'\n'; target.write_bytes(newbytes)
        with self.assertRaisesRegex(ValueError, 'changed since validation'):
            release.apply_plan(plan, self.backups)
        self.assertEqual(target.read_bytes(), newbytes)

    def test_backup_inside_public_root_and_existing_lock_rejected(self):
        plan = self.plan()
        with self.assertRaisesRegex(ValueError, 'outside the public'):
            release.apply_plan(plan, self.root / 'backups')
        lock = self.root / '.evidence-import.lock'; lock.write_text('another operation')
        with self.assertRaises(FileExistsError):
            release.apply_plan(plan, self.backups)
        self.assertEqual(lock.read_text(), 'another operation')


if __name__ == '__main__':
    unittest.main()
