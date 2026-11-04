"""Context relations must preserve evidence and publication authorship."""
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from entities import attach_entities, build_entity_pages


class ContextualEntitiesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records = json.loads((ROOT / 'data/catalogue.json').read_text())
        cls.entities = json.loads((ROOT / 'data/entities.json').read_text())

    def test_relations_preserve_authorship_and_input(self):
        original = json.dumps(self.records, sort_keys=True)
        enriched = attach_entities(self.records, self.entities)
        self.assertEqual(json.dumps(self.records, sort_keys=True), original)
        answerability = next(r for r in enriched if str(r['id']) == '23428974')
        links = {link['id']: link for link in answerability['entity_links']}
        self.assertEqual(links['dorian-vale']['relation'], 'author')
        self.assertEqual(links['museum-of-one']['relation'], 'publisher')
        self.assertEqual(links['reiko-tomii']['relation'], 'scholar discussed')
        self.assertEqual(links['shiraga-kazuo']['relation'], 'artist discussed')
        self.assertEqual(links['challenging-mud']['relation'], 'artwork discussed')
        self.assertIn('not a coauthor', links['reiko-tomii']['note'])
        self.assertEqual(answerability['creators'], next(r for r in self.records if str(r['id']) == '23428974')['creators'])

    def test_links_have_source_evidence_and_valid_targets(self):
        for record in attach_entities(self.records, self.entities):
            for link in record['entity_links']:
                self.assertTrue(link['source_url'].startswith('https://www.museumofone.art/'))
                self.assertTrue(link['note'])
        bad = [{'id': 'bad', 'label': 'Bad', 'type': 'Person', 'record_links': [
            {'record_id': 'missing', 'relation': 'artist discussed', 'source_url': 'https://example.org'}]}]
        with self.assertRaises(ValueError):
            attach_entities(self.records, bad)

    def test_pages_link_reciprocally_at_correct_depth(self):
        output = {}
        def layout(title, desc, body, **kwargs):
            return json.dumps({'title': title, 'body': body, **kwargs})
        paths = build_entity_pages(self.records, self.entities, output.__setitem__, layout, 'https://archive.example')
        self.assertEqual(len(paths), len(self.entities) + 3)
        self.assertTrue({'people.html', 'artworks.html', 'exhibitions.html'}.issubset(paths))
        artist = json.loads(output['entities/doris-salcedo.html'])
        artwork = json.loads(output['entities/atrabiliarios.html'])
        self.assertEqual(artist['base'], '../')
        self.assertIn('href="atrabiliarios.html"', artist['body'])
        self.assertIn('href="doris-salcedo.html"', artwork['body'])
        self.assertIn('href="../items/19863836.html"', artwork['body'])
        self.assertEqual(artwork['schema']['creator'][0]['name'], 'Doris Salcedo')
        tomii = json.loads(output['entities/reiko-tomii.html'])
        self.assertNotIn('author', tomii['schema'])


if __name__ == '__main__':
    unittest.main()
