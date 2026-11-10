"""Publication guardrails for the scoped WDW evidence collection."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('wdw_sources', ROOT / 'scripts/wdw_sources.py')
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class WDWSourceTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((ROOT / 'data/wdw-evidence.json').read_text())

    def test_hosted_file_matches_verified_source(self):
        MODULE._validate(self.data, ROOT)
        hosted = [r for r in self.data['records'] if r.get('hostedUrl')]
        self.assertEqual([r['id'] for r in hosted], ['wielocha-distributed-identity'])
        self.assertEqual(hosted[0]['licenceUrl'], 'https://creativecommons.org/licenses/by-nc/4.0/')

    def test_missing_permission_or_altered_bytes_block_publication(self):
        for field, value in [('hostingDecision', 'link-only'), ('attribution', ''), ('sha256', '0' * 64)]:
            data = deepcopy(self.data)
            row = next(r for r in data['records'] if r.get('hostedUrl'))
            row[field] = value
            with self.assertRaises(ValueError):
                MODULE._validate(data, ROOT)

    def test_private_copy_paths_not_exported(self):
        encoded = json.dumps(self.data)
        self.assertNotIn('/Users/', encoded)
        self.assertNotIn('work/journal/', encoded)
        self.assertNotIn('localResearchCopy', encoded)

    def test_each_record_has_one_display_group_and_unique_anchor(self):
        groups = {'Rim Dong Sik', 'Kim Kulim', 'Sung Neung Kyung', 'Comparative scholarship'}
        self.assertTrue(all(r['relatedCase'][0] in groups for r in self.data['records']))
        data = deepcopy(self.data)
        data['records'].append(deepcopy(data['records'][0]))
        with self.assertRaises(ValueError):
            MODULE._validate(data, ROOT)


if __name__ == '__main__':
    unittest.main()
