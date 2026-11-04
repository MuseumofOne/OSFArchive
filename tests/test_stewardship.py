"""Preservation checks must detect loss, change and unsafe recovery packages."""
import io
import json
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import stewardship


class Stewardship(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / 'archive'
        (self.root / 'data/source').mkdir(parents=True)
        (self.root / 'dist/assets/documents').mkdir(parents=True)
        (self.root / 'data/source/123.json').write_text('{"id":123}\n')
        (self.root / 'data/catalogue.json').write_text('[{"id":"123"}]\n')
        (self.root / 'dist/assets/documents/123.pdf').write_bytes(b'%PDF-1.7\nfixture content\n')
        self.report = stewardship.new_report()
        stewardship.refresh_inventory(self.root, self.report)

    def test_verify_detects_changed_missing_and_new_content_without_rebaseline(self):
        baseline = json.dumps(self.report['inventory'], sort_keys=True)
        self.assertEqual(stewardship.verify_inventory(self.root, self.report)['status'], 'passed')
        (self.root / 'data/catalogue.json').write_text('[]\n')
        (self.root / 'data/source/123.json').unlink()
        (self.root / 'data/new.json').write_text('{}')
        result = stewardship.verify_inventory(self.root, self.report)
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['changed'], ['data/catalogue.json'])
        self.assertEqual(result['missing'], ['data/source/123.json'])
        self.assertEqual(result['added'], ['data/new.json'])
        self.assertEqual(json.dumps(self.report['inventory'], sort_keys=True), baseline)

    def test_report_events_do_not_change_content_baseline(self):
        baseline = stewardship.inventory(self.root)
        stewardship.save_report(self.root, self.report)
        stewardship.verify_inventory(self.root, self.report)
        stewardship.save_report(self.root, self.report)
        self.assertEqual(stewardship.inventory(self.root), baseline)
        self.assertEqual(self.report['last_check']['status'], 'passed')

    def test_backup_performs_full_restore_and_compares_all_hashes(self):
        package = Path(self.tmp.name) / 'archive-backup.tar.gz'
        result = stewardship.create_backup(self.root, self.report, package)
        self.assertTrue(package.exists())
        self.assertEqual(result['restoration']['files_restored'], 3)
        self.assertEqual(result['restoration']['status'], 'passed')
        self.assertEqual(result['package_sha256'], stewardship.sha256(package))
        self.assertNotIn(self.tmp.name, json.dumps(self.report))
        self.assertIn('not an independent offsite backup', result['storage_scope'])

    def test_backup_inside_repository_is_rejected(self):
        with self.assertRaises(ValueError):
            stewardship.create_backup(self.root, self.report, self.root / 'backup.tar.gz')

    def test_restore_rejects_traversal_and_tampered_content(self):
        package = Path(self.tmp.name) / 'unsafe.tar.gz'
        for name in ['../escape', 'data/catalogue.json']:
            with self.subTest(name=name):
                with tarfile.open(package, 'w:gz') as archive:
                    payload = b'tampered'
                    member = tarfile.TarInfo(name)
                    member.size = len(payload)
                    archive.addfile(member, io.BytesIO(payload))
                with self.assertRaises(ValueError):
                    stewardship.restore_and_verify(package, self.report['inventory'])

    def test_public_evidence_page_exposes_only_relative_content_references(self):
        stewardship.verify_inventory(self.root, self.report)
        stewardship.save_report(self.root, self.report)
        output = {}
        def layout(title, description, content, path):
            return '<html><title>' + title + '</title>' + content + '</html>'
        with patch.object(stewardship, 'ROOT', self.root):
            pages = stewardship.build_stewardship_page([{'id': '123'}], output.__setitem__, layout, 'https://example.org')
        self.assertEqual(pages, ['stewardship.html'])
        self.assertIn('metadata/stewardship.json', output)
        self.assertIn('data/source/123.json', output['metadata/fixity-sha256.txt'])
        self.assertNotIn(self.tmp.name, ''.join(output.values()))
        self.assertIn('not an independent offsite backup', output['stewardship.html'])


if __name__ == '__main__':
    unittest.main()
