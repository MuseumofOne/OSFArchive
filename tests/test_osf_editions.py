import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from osf_editions import attach_osf_editions

class ExactEditionAccess(unittest.TestCase):
    def setUp(self):
        self.rows = json.loads((ROOT / 'data/osf-editions.json').read_text())
        self.catalogue = json.loads((ROOT / 'data/catalogue.json').read_text())
        copies = {r['id']: r for r in json.loads((ROOT / 'data/readers.json').read_text())}
        for r in self.catalogue:
            r['reading_copy'] = copies[r['id']]

    def test_every_selected_edition_has_one_exact_copy(self):
        result = attach_osf_editions(self.catalogue, ROOT)
        self.assertEqual(len(result), 16)
        self.assertEqual(len({r['osf_copy']['osf_guid'] for r in result}), 16)
        for r in result:
            self.assertEqual(r['doi'], r['osf_copy']['edition_doi'])
            self.assertTrue(any(a['field'] == 'osf_copy' for a in r['field_assertions']))

    def rejected(self, field, value):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            (root / 'data').mkdir()
            rows = copy.deepcopy(self.rows)
            rows[0][field] = value
            (root / 'data/osf-editions.json').write_text(json.dumps(rows))
            # The first mapping must fail before a PDF is opened.
            with self.assertRaises(ValueError):
                attach_osf_editions(copy.deepcopy(self.catalogue), root)

    def test_private_project_excluded(self):
        self.rejected('public_project', 'unapproved-project')

    def test_other_edition_rejected(self):
        self.rejected('edition_doi', '10.5281/zenodo.1')

    def test_changed_bytes_rejected(self):
        self.rejected('sha256', '0' * 64)

    def test_graph_relates_osf_to_the_edition_without_sameas(self):
        for r in json.loads((ROOT / 'dist/metadata/catalogue.json').read_text())['records']:
            graph = json.loads((ROOT / 'dist/metadata' / (r['id'] + '.jsonld')).read_text())['@graph']
            media = next(n for n in graph if n.get('@id') == r['osf_copy']['osf_url'] + '#file')
            self.assertEqual(media['encodesCreativeWork']['@id'], 'https://doi.org/' + r['doi'])
            self.assertNotIn('sameAs', media)
            self.assertEqual(media['identifier']['value'], r['reading_copy']['sha256'])
