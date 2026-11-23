"""Context relations must preserve evidence and publication authorship."""
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from entities import attach_entities, build_entity_pages, canonical_author_profiles, entity_graph


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

    def test_public_exchange_count_and_preserved_capture_are_visible(self):
        output = {}
        def layout(title, desc, body, **kwargs):
            return json.dumps({'description': desc, 'body': body, **kwargs})
        koh = next(entity for entity in self.entities if entity['id'] == 'dong-yeon-koh')
        source = koh['web_links'][0]['url']
        capture = 'website/web-abcdef0123456789abcdef01.html'
        origin = 'https://archive.example'
        build_entity_pages(self.records, self.entities, output.__setitem__, layout, origin,
                           website_captures={source: capture})
        directory = json.loads(output['people.html'])['body']
        card = directory.split('id="dong-yeon-koh"', 1)[1].split('</article>', 1)[0]
        self.assertIn('1 linked exchange', card)
        self.assertNotIn('linked publications', card)
        page = json.loads(output['entities/dong-yeon-koh.html'])
        self.assertIn(f'href="../{capture}"', page['body'])
        self.assertIn(f'href="{source}"', page['body'])
        self.assertEqual(page['schema']['subjectOf'][-1]['@id'], f'{origin}/{capture}#record')
        self.assertEqual(page['schema']['subjectOf'][-1]['isBasedOn'], {'@id': source})
        lee = json.loads(output['entities/lee-kang-so.html'])
        self.assertIn('Lee Kang-so', lee['description'])

    def test_publisher_profile_requires_an_attributed_author_source(self):
        vale = next(entity for entity in self.entities if entity['id'] == 'dorian-vale')
        author_source, other_source = [
            link['source_url'] for link in vale['record_links'] if link['relation'] == 'author'
        ][:2]
        url = 'https://www.museumofone.art/author/dorianvale/'
        author = {'name': 'Dorian Vale', 'url': url}
        captures = [{'source': {'url': author_source, 'creators': [author]}}]
        profiles = canonical_author_profiles(self.entities, captures)
        self.assertEqual(profiles, {'dorian-vale': url})
        output = {}
        def layout(title, desc, body, **kwargs):
            return json.dumps({'body': body, **kwargs})
        build_entity_pages(self.records, self.entities, output.__setitem__, layout, 'https://archive.example',
                           author_profiles=profiles)
        page = json.loads(output['entities/dorian-vale.html'])
        self.assertIn(f'href="{url}"', page['body'])
        self.assertEqual(page['schema']['sameAs'], [url])
        self.assertNotIn('affiliation', page['schema'])
        alternate = dict(author, url='https://www.museumofone.art/author/second-profile/')
        captures.append({'source': {'url': other_source, 'creators': [alternate]}})
        self.assertFalse(canonical_author_profiles(self.entities, captures))

    def test_dialogue_authorities_attach_to_archival_copies_and_originals(self):
        out = {}
        def layout(title, desc, body, **kwargs):
            return json.dumps({'body': body, **kwargs})
        origin = 'https://archive.example'
        paths = {
            'https://www.museumofone.art/lu-peng/': 'website/web-abcdef0123456789abcdef01.html',
            'https://www.museumofone.art/tomoki-akimaru/': 'website/web-abcdef0123456789abcdef02.html',
        }
        build_entity_pages(self.records, self.entities, out.__setitem__, layout, origin,
                           website_captures=paths)
        for name, original in (('lu-peng', 'https://mp.weixin.qq.com/s?'),
                               ('tomoki-akimaru', 'https://critique.aicajapan.com/19726')):
            page = json.loads(out['entities/' + name + '.html'])
            published = 'https://www.museumofone.art/' + name + '/'
            self.assertIn(f'href="../{paths[published]}"', page['body'])
            self.assertIn(f'href="{original}', page['body'])
            self.assertEqual(page['schema']['subjectOf'][-1]['isBasedOn'], {'@id': published})
            self.assertTrue({'author', 'affiliation', 'sameAs'}.isdisjoint(page['schema']))
        self.assertIn('https://critique.aicajapan.com/19740', out['entities/tomoki-akimaru.html'])

    def test_museum_authority_connects_to_the_reviewed_official_identity(self):
        origin = 'https://archive.example'
        out = {}
        def layout(title, desc, body, **kwargs):
            return json.dumps({'body': body, **kwargs})
        build_entity_pages(self.records, self.entities, out.__setitem__, layout, origin)
        page = json.loads(out['entities/museum-of-one.html'])
        homepage = 'https://www.museumofone.art/'
        self.assertIn(f'<dt>Institutional website</dt><dd><a href="{homepage}"', page['body'])
        self.assertEqual(page['schema']['@id'], origin + '/entities/museum-of-one.html#entity')
        self.assertEqual(page['schema']['sameAs'], [homepage + '#organization'])
        node = next(n for n in entity_graph(self.entities, origin)['@graph'] if n['@id'] == page['schema']['@id'])
        self.assertEqual(node, page['schema'])
        institution = next(e for e in self.entities if e['id'] == 'museum-of-one')
        unverified = dict(institution, identifiers=[dict(institution['identifiers'][0],
                                                       source_url='https://unverified.example/')])
        self.assertNotIn('sameAs', entity_graph([unverified], origin)['@graph'][0])


if __name__ == '__main__':
    unittest.main()
