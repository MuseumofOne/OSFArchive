"""Ensure the controlled access layer remains accountable to its source data."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from vocabulary import attach_vocabulary, build_vocabulary_pages, vocabulary_graph


class ControlledVocabulary(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.vocab = json.loads((ROOT / 'data/vocabulary.json').read_text())
        cls.records = json.loads((ROOT / 'data/catalogue.json').read_text())
        cls.terms = {t['id']: t for t in cls.vocab['terms']}

    def test_every_assignment_is_documented_without_altering_source_keywords(self):
        before = deepcopy(self.records)
        attached = attach_vocabulary(self.records, self.vocab)
        self.assertEqual(self.records, before)
        for original, result in zip(before, attached):
            self.assertEqual(original['keywords'], result['keywords'])
            self.assertEqual(original['subjects'], result['subjects'])
            self.assertEqual(original['type'], result['type'])
            self.assertTrue(all(any(label.casefold() in {x.casefold() for x in [t['label']]+t['alternative_labels']} for t in result['controlled_subjects']) for label in original['subjects']))
            self.assertEqual(len({t['id'] for t in result['controlled_subjects']}), len(result['controlled_subjects']))
            self.assertEqual(result['genre_terms'][0]['label'], original['type'])
            for assigned in result['controlled_subjects'] + result['genre_terms']:
                self.assertIn(assigned['id'], self.terms)
                self.assertIn('#' + assigned['id'], assigned['uri'])
                self.assertEqual(assigned['assignment_provenance']['status'], 'local_editorial_access_term')
        self.assertEqual(attached, attach_vocabulary(attached, self.vocab))

    def test_terms_have_warrant_and_reciprocal_relationships(self):
        self.assertEqual(len(self.terms), len(self.vocab['terms']))
        self.assertEqual(len({t['persistent_id'] for t in self.terms.values()}), len(self.terms))
        for term in self.terms.values():
            with self.subTest(term=term['id']):
                for field in ('definition', 'scope_note', 'editorial_owner', 'modified', 'mapping_note'):
                    self.assertTrue(term[field])
                self.assertGreaterEqual(term['version'], 4)
                self.assertLessEqual(term['version'], self.vocab['scheme']['version'])
                self.assertTrue(term['provenance']['source_urls'])
                for broader in term['broader']:
                    self.assertIn(term['id'], self.terms[broader]['narrower'])
                for narrower in term['narrower']:
                    self.assertIn(term['id'], self.terms[narrower]['broader'])
                for related in term['related']:
                    self.assertIn(term['id'], self.terms[related]['related'])

    def test_undocumented_access_terms_require_editorial_review(self):
        record = deepcopy(self.records[0])
        record['subjects'].append('A future direction')
        with self.assertRaisesRegex(ValueError, 'Undocumented editorial subject'):
            attach_vocabulary([record], self.vocab)
        record = deepcopy(self.records[0])
        record['type'] = 'Oral history'
        with self.assertRaisesRegex(ValueError, 'Undocumented resource genre'):
            attach_vocabulary([record], self.vocab)

    def test_local_framework_does_not_inherit_external_equivalence(self):
        for term in self.terms.values():
            if term['kind'] == 'local-framework-concept':
                self.assertEqual(term['mapping_status'], 'not_asserted')
                self.assertEqual(term['external_mappings'], [])
        book = self.terms['genre-book']['external_mappings'][0]
        self.assertEqual(book['relation'], 'relatedMatch')
        self.assertIn('physical', book['note'])
        article = self.terms['genre-journal-article']['external_mappings'][0]
        self.assertEqual(article['relation'], 'broadMatch')
        self.assertEqual(article['uri'], 'http://vocab.getty.edu/aat/300048715')

    def test_exports_keep_hierarchy_and_checked_mappings(self):
        origin = 'https://archive.example'
        graph = vocabulary_graph(self.vocab, origin)
        nodes = {n['@id']: n for n in graph['@graph']}
        for term in self.terms.values():
            node = nodes[origin + '/vocabulary.html#' + term['id']]
            self.assertEqual(node['dct:identifier'], term['persistent_id'])
            self.assertEqual(node['skos:prefLabel']['@value'], term['preferred_label'])
            self.assertNotIn('skos:exactMatch', node)
        self.assertEqual(nodes[origin+'/vocabulary.html#genre-journal-article']['skos:broadMatch'], [{'@id':'http://vocab.getty.edu/aat/300048715'}])
        outputs = {}
        def layout(title, desc, body, path, schema=None):
            self.assertEqual(schema, graph)
            return '<html><body>' + body + '</body></html>'
        paths = build_vocabulary_pages(self.records, self.vocab, outputs.__setitem__, layout, origin)
        self.assertEqual(paths, ['vocabulary.html'])
        self.assertIn('id="post-interpretive-criticism"', outputs['vocabulary.html'])
        self.assertIn('vocabulary-filter', outputs['vocabulary.html'])
        self.assertEqual(json.loads(outputs['metadata/vocabulary.jsonld']), graph)
        self.assertEqual(json.loads(outputs['metadata/vocabulary.json']), self.vocab)


if __name__ == '__main__':
    unittest.main()
