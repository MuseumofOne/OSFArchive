"""Public release boundaries and evidence-preserving discovery generation."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from discovery_v2 import build_discovery_page, build_research_discovery, build_fulltext_index, encode_index
from enrich import enrich_record
from entities import attach_entities
from contents import attach_contents
from vocabulary import attach_vocabulary
from readers import apply_reading_metadata
from pirr import attach_pirr, load_pirr
from publication_arrangement import publication_inventory


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

    def test_standalone_results_have_a_section_heading(self):
        output = {}
        build_discovery_page(output.__setitem__, lambda title, desc, body, path: body, self.feed, self.origin)
        self.assertIn('<h2 class="sr-only">Search results</h2><ol class="discovery-results"', output['research-discovery.html'])

    def test_standalone_evidence_collection_label_retains_its_filter_key(self):
        output = {}
        feed = {'records': [{'title': 'Example evidence', 'url': self.origin + '/evidence.html',
                             'kind': 'evidence', 'collection': 'rai-published-research'}]}
        build_discovery_page(output.__setitem__, lambda title, desc, body, path: body, feed, self.origin)
        self.assertIn('<option value="rai-published-research">Published RAI research: Korean art comparisons</option>',
                      output['research-discovery.html'])

    def build(self, **changes):
        values = dict(records=self.records, entities=self.entities, vocab=self.vocab, programmes=self.programmes, origin=self.origin)
        values.update(changes)
        return build_research_discovery(**values)

    def test_all_described_levels_are_search_destinations(self):
        self.assertEqual(self.feed['counts'], {'publication': 22, 'chapter': 57, 'entity': 46, 'concept': 63, 'programme': 12})
        lu_peng = next(r for r in self.feed['records'] if r['id'] == 'programme:research-chinese-art-historiography')
        self.assertEqual(lu_peng['identifiers'], ['pir-prj-br3k2hk9'])
        self.assertEqual(lu_peng['kind'], 'programme')
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
        self.assertEqual(feed['counts']['programme'], 11)

    def test_website_records_need_explicit_public_evidence_and_allowed_origin(self):
        page = dict(url='https://www.museumofone.art/example/', source_url='https://www.museumofone.art/example/', title='Example writing', public=True, reviewed='2026-11-04', source_sha256='a' * 64, text='Original public page text.')
        feed = self.build(ghost_records=[page])
        self.assertEqual(feed['counts']['website'], 1)
        for changes in ({'public': False}, {'private': True}, {'source_sha256': ''}, {'source_url': 'https://example.org/'}, {'url': 'https://example.org/'}):
            with self.assertRaisesRegex(ValueError, 'public-source evidence'):
                self.build(ghost_records=[{**page, **changes}])

    def test_reviewed_website_dois_apply_only_to_the_checked_source(self):
        sources = {
            'nomadic-aesthetics-travelling-installations-as-moral-geography': ('17478280', 'version_family'),
            'a-museum-of-breath-designing-spaces-for-attention-not-spectacle': ('18349238', 'version_family'),
            'formal-defence-of-post-interpretive-criticism': ('16934437', 'deposited_version'),
            'duchamp': ('17056223', 'deposited_version'),
        }
        all_dois = ' '.join('10.5281/zenodo.' + rid for rid, _ in sources.values())
        pages, captures = [], []
        for i, slug in enumerate([*sources, 'archives']):
            url = 'https://www.museumofone.art/' + slug + '/'
            title = slug.replace('-', ' ').title()
            pages.append(dict(url=url, source_url=url, title=title, public=True,
                              reviewed='2026-11-25', source_sha256='a' * 64, text=all_dois))
            captures.append({
                'source': dict(url=url, title=title, kind='post', published_at='2026-11-25',
                               updated_at='2026-11-25'),
                'archive_id': f'web-{i:024x}', 'summary': '',
                'original_published_at': '2026-11-25', 'first_captured_at': '2026-11-25',
                'capture': {'captured_at': '2026-11-25'},
            })
        inventory = publication_inventory(captures, self.records)
        feed = self.build(ghost_records=pages, website_inventory=inventory)
        by_url = {row['url']: row for row in feed['records'] if row['kind'] == 'website'}
        by_source = {row['source_url']: row for row in inventory}
        for page in pages[:-1]:
            url = page['url']
            slug = url.rstrip('/').rsplit('/', 1)[-1]
            rid, scope = sources[slug]
            doi = '10.5281/zenodo.' + rid
            row = by_url[url]
            association = by_source[url]['related_publication_doi']
            self.assertEqual(association['scope'], scope)
            self.assertEqual(association['source_field'], 'citation_doi')
            self.assertEqual(row['identity'], url)
            self.assertEqual(row['identifiers'], [doi])
            self.assertEqual(row['identifier_scopes'], {doi: association['scope_label']})
            self.assertEqual(row['sources'][1]['url'], 'https://api.datacite.org/dois/' + doi)
        archives = pages[-1]['url']
        self.assertIn('10.5281/zenodo.16934437', by_url[archives]['search_text'])
        self.assertEqual(by_url[archives]['identifiers'], [])
        self.assertNotIn('related_publication_doi', by_source[archives])

    def test_gladston_dialogue_edges_require_a_verified_public_capture(self):
        source_url = 'https://www.museumofone.art/paul-gladston/'
        page = dict(url=source_url, source_url=source_url, title='Paul Gladston programme',
                    public=True, reviewed='2026-11-04', source_sha256='a' * 64)
        entity_id = 'entity:paul-gladston'
        relationship = 'dialogue participation documented in'

        offline_entity = next(record for record in self.feed['records'] if record['id'] == entity_id)
        self.assertFalse(any(edge['relation'] == relationship for edge in offline_entity['relationships']))

        records = self.build(ghost_records=[page])['records']
        entity = next(record for record in records if record['id'] == entity_id)
        capture = next(record for record in records if record.get('original_url') == source_url
                       and record['kind'] == 'website')
        for source, target, relation in ((entity, capture, relationship),
                                         (capture, entity, 'describes dialogue participation')):
            edges = [edge for edge in source['relationships'] if edge['relation'] == relation]
            self.assertEqual(
                [(edge['target_id'], edge['source_url'], edge['evidence_scope']) for edge in edges],
                [(target['id'], source_url, 'public programme record')],
            )

        with self.assertRaisesRegex(ValueError, 'public-source evidence'):
            self.build(ghost_records=[{**page, 'public': False}])

    def test_lu_and_akimaru_links_preserve_publication_roles(self):
        aliases = {'lu-peng': '吕澎', 'tomoki-akimaru': '秋丸知貴'}
        originals = {
            'lu-peng': ('https://mp.weixin.qq.com/s?',),
            'tomoki-akimaru': ('https://critique.aicajapan.com/19726', 'https://critique.aicajapan.com/19740'),
        }
        pages = []
        for person in aliases:
            url = 'https://www.museumofone.art/' + person + '/'
            pages.append(dict(url=url, source_url=url, title=person, public=True,
                              reviewed='2026-11-23', source_sha256='a' * 64))
        rows = self.build(ghost_records=pages)['records']
        for person, alias in aliases.items():
            source = 'https://www.museumofone.art/' + person + '/'
            authority = next(row for row in rows if row['id'] == 'entity:' + person)
            record = next(row for row in rows if row.get('original_url') == source)
            self.assertIn(alias, authority['aliases'])
            self.assertEqual(authority['identifiers'], ['MOO-CTX-' + person])
            self.assertTrue(all(any(x['url'].startswith(url) for x in authority['sources'])
                                for url in originals[person]))
            for here, there in ((authority, record), (record, authority)):
                self.assertEqual([(edge['target_id'], edge['source_url'], edge['evidence_scope'])
                                  for edge in here['relationships']],
                                 [(there['id'], source, 'published dialogue record')])

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
            source_url = record['institutional_url']
            record['institutional_url'] = source_url.replace('://www.', '://').rstrip('/')
            page = dict(url=source_url, source_url=source_url, title='Verified web description', public=True, reviewed='2026-11-04', source_sha256='a' * 64)
            inventory = [dict(source_url=source_url, collection=record['collection'], aliases=[],
                              subjects=[], date=record['date'], role='Website version',
                              edition_path='items/' + record['id'] + '.html',
                              capture_path='website/web-' + 'b' * 24 + '.html')]
            feed = self.build(records=records, ghost_records=[page], website_inventory=inventory)
            website = next(r for r in feed['records'] if r['kind'] == 'website')
            publication = next(r for r in feed['records'] if r['id'] == 'publication:' + record['id'])
            self.assertFalse(website['catalogue_record'])
            self.assertEqual(publication['original_url'], source_url)
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

    def test_japanese_artist_name_keeps_entity_and_publication_scopes_distinct(self):
        rows = {r['id']: r for r in self.feed['records']}
        artist = rows['entity:shiraga-kazuo']
        publication = rows['publication:23428974']
        self.assertIn('白髪一雄', artist['aliases'])
        self.assertIn('白髪一雄', artist['search_text'])
        self.assertTrue(any(s['url'] == 'https://artplatform.go.jp/artists/A1478'
                            for s in artist['sources']))
        self.assertIn('白髪一雄', publication['search_text'])
        self.assertNotIn('白髪一雄', publication['aliases'])
        self.assertEqual(publication['author'], 'Dorian Vale')
        self.assertTrue(any(e['target_id'] == artist['id'] and
                            e['relation'] == 'artist discussed'
                            for e in publication['relationships']))

    def test_fulltext_fixity_and_verbatim_page_evidence(self):
        import fitz
        feed = build_fulltext_index(self.records, ROOT, self.origin)
        self.assertEqual(feed['counts'], {'documents': 22, 'pages': 820, 'searchable_pages': 806})
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
