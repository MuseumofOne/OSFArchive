"""Research references preserve namespaces, source scope and reciprocal access."""
from copy import deepcopy
import csv
from io import StringIO
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from contents import attach_contents
from pirr import attach_pirr, build_pirr_pages, load_pirr, pirr_item_panel


class PirrCrosswalkTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records = json.loads((ROOT / 'data/catalogue.json').read_text())
        cls.programmes = json.loads((ROOT / 'data/programmes.json').read_text())
        cls.data = load_pirr()

    def test_identifiers_keep_source_namespaces_and_publication_identity(self):
        originals = json.dumps([self.records, self.programmes], sort_keys=True)
        records, programmes = attach_pirr(self.records, self.programmes, self.data)
        self.assertEqual(originals, json.dumps([self.records, self.programmes], sort_keys=True))
        self.assertEqual(sum(bool(r['pirr_references']) for r in records), 13)
        self.assertEqual(sum(len(p['identifiers']) for p in self.data['programmes']), 7)
        methods = next(p for p in programmes if '/research-methods/' in p['url'])
        self.assertEqual(methods['pirr_project_id'], 'pir-prj-pyp5yx3w')
        self.assertNotIn('pirr_reference', methods)
        markov = next(p for p in programmes if '/research-critical-language/' in p['url'])
        self.assertEqual(markov['pirr_reference'], 'moo-program-2b3ad664cbd92f69b862db8c')
        paper = next(r for r in records if str(r['id']) == '23430200')
        self.assertEqual(paper['pirr_work_identity']['edition_doi'], '10.5281/zenodo.23430200')
        self.assertEqual(paper['creators'], next(r for r in self.records if str(r['id']) == '23430200')['creators'])
        self.assertNotIn('pirr_work_id', paper)
        self.assertTrue(paper['pirr_references'][0]['source_url'].startswith('https://www.museumofone.art/'))

    def test_rejects_relabelled_ids_and_unsourced_programme_links(self):
        bad = deepcopy(self.data)
        bad['programmes'][0]['identifiers'][0]['scheme'] = 'PIRR project ID'
        with self.assertRaisesRegex(ValueError, 'namespace'):
            attach_pirr(self.records, self.programmes, bad)
        bad = deepcopy(self.data)
        bad['programme_relations'][0]['to'] = 'missing'
        with self.assertRaisesRegex(ValueError, 'Unresolved'):
            attach_pirr(self.records, self.programmes, bad)

    def test_pages_link_programmes_publications_components_and_exports(self):
        records = attach_contents(deepcopy(self.records), json.loads((ROOT / 'data/contents.json').read_text()))
        output = {}
        def layout(title, description, body, **kwargs):
            return json.dumps({'title': title, 'body': body, **kwargs})
        paths = build_pirr_pages(records, self.programmes, self.data, output.__setitem__, layout, 'https://archive.example')
        self.assertEqual(paths, ['research-registry.html'])
        page = json.loads(output[paths[0]])
        self.assertIn('id="pir-prj-pyp5yx3w"', page['body'])
        self.assertIn('href="items/23430200.html"', page['body'])
        self.assertIn('href="parts/19864099-c001.html"', page['body'])
        self.assertIn('data-registry-entry', page['body'])
        self.assertIn('URLSearchParams', page['body'])
        exported = json.loads(output['data/research-crosswalk.json'])
        self.assertEqual(len(exported['publications']), len(records))
        self.assertEqual(sum(len(r['components']) for r in exported['publications']), 57)
        rows = list(csv.DictReader(StringIO(output['data/research-crosswalk.csv'])))
        methods = [r for r in rows if r['identifier'] == 'pir-prj-pyp5yx3w']
        self.assertEqual({r['identifier_scheme'] for r in methods}, {'PIRR project ID'})
        self.assertTrue(all(r['identifier_source'] for r in rows if r['identifier']))
        csv_identifiers = {r['identifier'] for r in rows if r['identifier']}
        source_identifiers = {i['value'] for p in self.data['programmes'] for i in p['identifiers']}
        self.assertEqual(csv_identifiers, source_identifiers)

    def test_item_links_are_reciprocal_without_making_programme_authors(self):
        records, _ = attach_pirr(self.records, self.programmes, self.data)
        paper = next(r for r in records if str(r['id']) == '23428974')
        panel = pirr_item_panel(paper)
        self.assertIn('href="../research-registry.html#reiko-tomii"', panel)
        self.assertIn('moo-program-fc96d462c463652ce260cd27', panel)
        no_link = next(r for r in records if str(r['id']) == '21786998')
        self.assertEqual(pirr_item_panel(no_link), '')


if __name__ == '__main__':
    unittest.main()
