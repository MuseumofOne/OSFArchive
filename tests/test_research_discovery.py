"""Public release boundaries and evidence-preserving discovery generation."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from discovery_v2 import build_research_discovery, build_fulltext_index, encode_index
from enrich import enrich_record
from entities import attach_entities
from contents import attach_contents
from vocabulary import attach_vocabulary
from readers import apply_reading_metadata
from pirr import attach_pirr, load_pirr


def inputs():
    load = lambda name: json.loads((ROOT / 'data' / (name + '.json')).read_text())
    entities, vocab = load('entities'), load('vocabulary')
    records = apply_reading_metadata([enrich_record(r, load('authorities')) for r in load('catalogue')], ROOT)
    records = attach_vocabulary(attach_contents(attach_entities(records, entities), load('contents')), vocab)
    records, programmes = attach_pirr(records, load('programmes'), load_pirr())
    return records, entities, vocab, programmes


class ResearchDiscovery(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records, cls.entities, cls.vocab, cls.programmes = inputs()
        cls.origin = 'https://archive.museumofone.art'
        cls.feed = build_research_discovery(cls.records, cls.entities, cls.vocab, cls.programmes, cls.origin)

    def build(self, **changes):
        values = dict(records=self.records, entities=self.entities, vocab=self.vocab, programmes=self.programmes, origin=self.origin)
        values.update(changes)
        return build_research_discovery(**values)

    def test_all_described_levels_are_search_destinations(self):
        self.assertEqual(self.feed['counts'], {'publication': 21, 'chapter': 57, 'entity': 44, 'concept': 62, 'programme': 10})
        ids = {r['id'] for r in self.feed['records']}
        for row in self.feed['records']:
            self.assertTrue(row['sources'], row['id'])
            for edge in row['relationships']:
                self.assertIn(edge['target_id'], ids)
                self.assertTrue(edge['source_url'])

    def test_content_hash_and_input_order_are_deterministic(self):
        second = self.build(records=list(reversed(self.records)))
        # Ordering inside evidence-bearing relationship arrays follows source
        # order; canonical record order does not depend on input order.
        self.assertEqual([r['id'] for r in second['records']], [r['id'] for r in self.feed['records']])
        data = dict(self.feed); signature = data.pop('content_version')
        self.assertEqual(signature, hashlib.sha256(encode_index(data).encode()).hexdigest())
        self.assertEqual(self.feed, self.build())

    def test_private_publication_fails_before_export(self):
        records = copy.deepcopy(self.records); records[0]['private'] = True
        with self.assertRaisesRegex(ValueError, 'not eligible for public export'):
            self.build(records=records)

    def test_private_entity_and_edges_do_not_leak(self):
        entities = copy.deepcopy(self.entities); entities[0]['private'] = True
        records = copy.deepcopy(self.records)
        for record in records:
            for entity in record.get('entity_links', []):
                if entity['id'] == entities[0]['id']:
                    entity['label'] = 'PRIVATE-EDITORIAL-SENTINEL'
                    entity['variants'] = ['PRIVATE-VARIANT-SENTINEL']
        feed = self.build(records=records, entities=entities); removed = 'entity:' + entities[0]['id']
        self.assertNotIn(removed, [r['id'] for r in feed['records']])
        self.assertFalse(any(e['target_id'] == removed for r in feed['records'] for e in r['relationships']))
        self.assertNotIn('PRIVATE-EDITORIAL-SENTINEL', encode_index(feed))
        self.assertNotIn('PRIVATE-VARIANT-SENTINEL', encode_index(feed))

    def test_unreviewed_or_out_of_bounds_component_stops_export(self):
        for change in ({'pdf_start': 0}, {'pdf_end': 999999}, {'evidence': {}}, {'private': True}):
            records = copy.deepcopy(self.records)
            next(r for r in records if r.get('contents'))['contents'][0].update(change)
            with self.assertRaisesRegex(ValueError, 'checked pagination'):
                self.build(records=records)

    def test_unsourced_programme_is_not_promoted(self):
        programmes = copy.deepcopy(self.programmes); programmes[0]['source_url'] = ''
        feed = self.build(programmes=programmes)
        self.assertEqual(feed['counts']['programme'], 9)

    def test_website_records_need_explicit_public_evidence_and_allowed_origin(self):
        page = dict(url='https://www.museumofone.art/example/', source_url='https://www.museumofone.art/example/', title='Example writing', public=True, reviewed='2026-11-04', source_sha256='a' * 64, text='Original public page text.')
        feed = self.build(ghost_records=[page])
        self.assertEqual(feed['counts']['website'], 1)
        for changes in ({'public': False}, {'private': True}, {'source_sha256': ''}, {'source_url': 'https://example.org/'}, {'url': 'https://example.org/'}):
            with self.assertRaisesRegex(ValueError, 'public-source evidence'):
                self.build(ghost_records=[{**page, **changes}])

    def test_related_names_are_not_alternative_titles_and_isbn_scope_is_visible(self):
        rows = {r['id']: r for r in self.feed['records']}
        for record in rows.values():
            if record['kind'] == 'publication':
                self.assertNotIn('Kazuo Shiraga', record['aliases'])
        self.assertIn('Title-level ISBN', rows['publication:19864099']['identifier_scopes']['978-1-06-982030-3'])

    def test_website_match_scope_survives_both_directions(self):
        for scope in ('exact_edition', 'version_family', 'work'):
            records = copy.deepcopy(self.records)
            record = next(r for r in records if r.get('institutional_url'))
            record['institutional_match_scope'] = scope
            record.setdefault('institutional_metadata', {})['linked_zenodo_dois'] = [record['doi']] if scope == 'exact_edition' else [record['conceptdoi']] if scope == 'version_family' else []
            page = dict(url=record['institutional_url'], source_url=record['institutional_url'], title='Verified web description', public=True, reviewed='2026-11-04', source_sha256='a' * 64)
            feed = self.build(records=records, ghost_records=[page])
            website = next(r for r in feed['records'] if r['kind'] == 'website')
            publication = next(r for r in feed['records'] if r['id'] == 'publication:' + record['id'])
            edges = [next(e for e in website['relationships'] if e['target_id'] == publication['id']), next(e for e in publication['relationships'] if e['target_id'] == website['id'])]
            for edge in edges:
                self.assertEqual(edge['institutional_match_scope'], scope)
                self.assertEqual(edge['evidence_scope'], scope)
                self.assertTrue(edge['note'])

    def test_entity_relationship_scope_is_consistent_in_both_directions(self):
        rows = {r['id']: r for r in self.feed['records']}
        for row in rows.values():
            if row['kind'] != 'entity':
                continue
            for edge in row['relationships']:
                if edge['target_id'].startswith('publication:'):
                    reverse = next(e for e in rows[edge['target_id']]['relationships'] if e['target_id'] == row['id'])
                    self.assertEqual(edge['evidence_scope'], reverse['evidence_scope'])

    def test_aliases_and_direct_chapter_access_are_preserved(self):
        rows = {r['id']: r for r in self.feed['records']}
        self.assertIn('Kazuo Shiraga', rows['entity:shiraga-kazuo']['aliases'])
        chapter = rows['chapter:19864099:c002']
        self.assertEqual(chapter['reader_url'], self.origin + '/read/19864099.html#page=9')
        self.assertNotIn('10.5281', ' '.join(chapter['identifiers']))
        self.assertEqual(chapter['identity'], chapter['url'] + '#component')

    def test_fulltext_fixity_and_verbatim_page_evidence(self):
        import fitz
        feed = build_fulltext_index(self.records, ROOT, self.origin)
        self.assertEqual(feed['counts'], {'documents': 21, 'pages': 811, 'searchable_pages': 797})
        documents = {d['id']: d for d in feed['documents']}
        for row in feed['records']:
            doc = documents[row['document_id']]
            self.assertEqual(row['source_sha256'], doc['sha256'])
            self.assertEqual(row['license'], doc['license'])
            self.assertLessEqual(row['page'], doc['page_count'])
        target = next(r for r in feed['records'] if r['id'] == 'passage:23430200:5')
        with fitz.open(ROOT / 'dist/assets/documents/23430200.pdf') as pdf:
            self.assertEqual(target['text'], pdf[4].get_text('text', sort=False))
        self.assertIn('#page=5', target['url'])
        altered = copy.deepcopy(self.records); altered[0]['reading_copy']['sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'fixity mismatch'):
            build_fulltext_index(altered, ROOT, self.origin)


if __name__ == '__main__':
    unittest.main()
