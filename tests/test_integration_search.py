"""Public integration feed: source eligibility, bibliographic scope and determinism."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from integration_search import (build_search_index, encode_search_index,
                                load_source_snapshots, publication_eligible, searchable_text)
from contents import attach_contents
from entities import attach_entities
from pirr import attach_pirr, load_pirr
from vocabulary import attach_vocabulary


class IntegrationSearchTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records = json.loads((ROOT / 'data/catalogue.json').read_text())
        cls.records = attach_entities(cls.records, json.loads((ROOT / 'data/entities.json').read_text()))
        cls.records = attach_contents(cls.records, json.loads((ROOT / 'data/contents.json').read_text()))
        cls.records = attach_vocabulary(cls.records, json.loads((ROOT / 'data/vocabulary.json').read_text()))
        cls.records, _ = attach_pirr(cls.records, [], load_pirr())
        cls.sources = load_source_snapshots(cls.records, ROOT / 'data/source')

    def test_all_current_items_are_source_verified_public_entries(self):
        before = encode_search_index([self.records, self.sources])
        payload = build_search_index(self.records, 'https://archive.museumofone.art/', self.sources)
        self.assertEqual(len(payload['records']), len(self.records))
        self.assertEqual(payload['schema_version'], 1)
        for entry in payload['records']:
            self.assertEqual(entry['url'], 'https://archive.museumofone.art/items/' + entry['id'] + '.html')
            self.assertEqual(entry['date_role'], 'repository_publication')
            self.assertNotIn('source_description_html', entry)
            self.assertNotIn('files', entry)
            self.assertEqual(entry['sources'][0]['role'], 'repository')
        self.assertEqual(before, encode_search_index([self.records, self.sources]))

    def test_unknown_draft_restricted_and_mismatched_records_fail_closed(self):
        original = self.records[0]
        source = self.sources[original['id']]
        for fields in [
            {'record_status': 'Draft'}, {'record_level': 'Component'}, {'private': True},
            {'draft': True}, {'is_draft': True}, {'public': False}, {'published': False},
            {'visibility': 'private'}, {'hidden': True}, {'zenodo_url': 'file:///private'},
            {'id': '../private'}, {'doi': '10.5281/zenodo.999'},
        ]:
            with self.subTest(fields=fields):
                record = {**original, **fields, 'summary': 'PRIVATE_SENTINEL'}
                payload = build_search_index([record], 'https://archive.example', {str(record['id']): source})
                self.assertEqual(payload['records'], [])
                self.assertNotIn('PRIVATE_SENTINEL', encode_search_index(payload))
        for fields in [{'submitted': False}, {'state': 'draft'}, {'is_published': False},
                       {'metadata': {'access_right': 'restricted'}}, {'id': 999}, {'doi': 'wrong'},
                       {'access': {'record': 'restricted'}},
                       {'access': {'record': 'public', 'files': 'restricted'}}]:
            self.assertFalse(publication_eligible(original, {**source, **fields}))
        self.assertFalse(publication_eligible(original, None))
        self.assertFalse(publication_eligible({**original, 'record_status': None}, source))

    def test_content_version_is_stable_and_tracks_public_content(self):
        payload = build_search_index(self.records, 'https://archive.example', self.sources)
        reordered = build_search_index(list(reversed(self.records)), 'https://archive.example', self.sources)
        self.assertEqual(encode_search_index(payload), encode_search_index(reordered))
        unhashed = {key: value for key, value in payload.items() if key != 'content_version'}
        self.assertEqual(payload['content_version'], sha256(encode_search_index(unhashed).encode()).hexdigest())
        changed = deepcopy(self.records)
        changed[0]['summary'] += ' Corrected description.'
        self.assertNotEqual(payload['content_version'], build_search_index(changed, 'https://archive.example', self.sources)['content_version'])
        self.assertNotEqual(payload['content_version'], build_search_index(self.records, 'https://other.example', self.sources)['content_version'])

    def test_programme_identifiers_and_analytic_terms_preserve_scope(self):
        payload = build_search_index(self.records, 'https://archive.example', self.sources)
        volume = next(r for r in payload['records'] if r['id'] == '19864099')
        methods = next(p for p in volume['programmes'] if p['id'] == 'research-methods')
        self.assertEqual(methods['identifiers'][0]['scheme'], 'PIRR project ID')
        self.assertEqual(methods['identifiers'][0]['value'], 'pir-prj-pyp5yx3w')
        self.assertEqual(methods['registry_url'], 'https://archive.example/research-registry.html#research-methods')
        self.assertTrue(methods['source_url'].startswith('https://www.museumofone.art/'))
        self.assertNotIn('identifiers', volume)  # Programme IDs are not work IDs.
        original = next(r for r in self.records if r['id'] == volume['id'])
        self.assertIn(original['contents'][0]['title'], volume['search_text'])
        self.assertIn('pir-prj-pyp5yx3w', volume['search_text'])
        self.assertEqual(searchable_text(original), volume['search_text'])

    def test_sourced_artist_variants_are_searchable_without_changing_work_identity(self):
        payload = build_search_index(self.records, 'https://archive.example', self.sources)
        answerability = next(r for r in payload['records'] if r['id'] == '23428974')
        for query in ('Shiraga Kazuo', 'Kazuo Shiraga', '白髪一雄'):
            self.assertIn(query, answerability['search_text'])
        original = next(r for r in self.records if r['id'] == '23428974')
        self.assertEqual(answerability['title'], original['title'])
        self.assertEqual(answerability['author'], original['author'])
        self.assertEqual(answerability['doi'], original['doi'])
        self.assertEqual(searchable_text(original), answerability['search_text'])

    def test_unapproved_fields_are_not_serialized_or_searchable(self):
        record = deepcopy(self.records[0])
        record['internal_notes'] = 'PRIVATE_SENTINEL'
        record['provenance']['internal_path'] = '/private/PRIVATE_SENTINEL'
        payload = build_search_index([record], 'https://archive.example', self.sources)
        self.assertNotIn('PRIVATE_SENTINEL', encode_search_index(payload))

    def test_source_review_dates_keep_their_source_specific_scope(self):
        record = deepcopy(self.records[0])
        record['source_review'] = '2030-01-01'
        record['institutional_metadata']['reviewed'] = '2020-01-01'
        payload = build_search_index([record], 'https://archive.example', self.sources)
        repository, institution = payload['records'][0]['sources']
        self.assertEqual(repository['reviewed'], '2030-01-01')
        self.assertEqual(institution['reviewed'], '2020-01-01')
        del record['institutional_metadata']['reviewed']
        payload = build_search_index([record], 'https://archive.example', self.sources)
        self.assertNotIn('reviewed', payload['records'][0]['sources'][1])

    def test_github_project_base_path_and_string_creator_are_supported(self):
        record = deepcopy(self.records[0])
        record['creators'] = ['Vale, Dorian']
        base = 'https://museumofone.github.io/OSFArchive'
        payload = build_search_index([record], base + '/', self.sources)
        self.assertEqual(payload['canonical_origin'], base)
        self.assertEqual(payload['records'][0]['url'], base + '/items/' + record['id'] + '.html')
        self.assertIn('Vale, Dorian', payload['records'][0]['search_text'])

    def test_sources_are_confined_and_missing_or_malformed_data_is_omitted(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / '19864099.json').write_text(json.dumps(self.sources['19864099']))
            (root / '19864115.json').write_text('malformed')
            loaded = load_source_snapshots(self.records + [{'id': '../secret'}], root)
            self.assertEqual(set(loaded), {'19864099'})
            self.assertEqual(len(build_search_index(self.records, 'https://archive.example', loaded)['records']), 1)

    def test_invalid_origins_and_duplicate_public_records_are_rejected(self):
        for origin in ['http://archive.example', 'https://archive.example/../secret',
                       'https://archive.example/%2e%2e/secret', 'https://archive.example//path',
                       'https://archive.example/?q=x', 'https://user:secret@archive.example',
                       'file:///tmp/archive', 'https://archive.example/#frag']:
            with self.subTest(origin=origin), self.assertRaises(ValueError):
                build_search_index(self.records, origin, self.sources)
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            build_search_index([self.records[0], self.records[0]], 'https://archive.example', self.sources)


if __name__ == '__main__':
    unittest.main()
