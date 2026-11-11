"""Cross-export regressions for identity and evidence scope, not only JSON syntax."""
from copy import deepcopy
from html import escape
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from identities import entity_uri, work_uri, institutional_scope, edition_isbn
from metadata import build_graph, build_dc
from metadata_profile import (prepare_metadata_records, validate_metadata_profile, validate_global_graph,
                              build_quality_report, require_valid_report, combine_graphs, validate_export_agreement)
from relationship_assertions import typed_relationship_assertions
from enrich import enrich_record
from readers import apply_reading_metadata
from entities import attach_entities, entity_graph
from contents import attach_contents, component_schema
from vocabulary import attach_vocabulary, vocabulary_graph
from policies import attach_catalogue_history
from citations import build_citation_model, csl_json, bibtex, ris, scholar_meta

ORIGIN = 'https://archive.example'


class MetadataProfileTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        raw = json.loads((ROOT / 'data/catalogue.json').read_text())
        authorities = json.loads((ROOT / 'data/authorities.json').read_text())
        cls.entities = json.loads((ROOT / 'data/entities.json').read_text())
        cls.vocabulary = json.loads((ROOT / 'data/vocabulary.json').read_text())
        cls.vocabulary['scheme']['base_uri'] = ORIGIN + '/vocabulary.html'
        contents = json.loads((ROOT / 'data/contents.json').read_text())
        rows = attach_entities(apply_reading_metadata([enrich_record(r, authorities) for r in raw], ROOT), cls.entities)
        rows = attach_catalogue_history(attach_vocabulary(attach_contents(rows, contents), cls.vocabulary))
        cls.records = prepare_metadata_records(rows, ORIGIN)
        cls.by_id = {r['id']: r for r in cls.records}

    def graph(self, record):
        return build_graph(record, ORIGIN + '/items/' + record['id'] + '.html', ORIGIN)

    def all_graphs(self):
        graphs = [self.graph(r) for r in self.records]
        graphs += [component_schema(r, part, ORIGIN) for r in self.records for part in r.get('contents', [])]
        graphs += [vocabulary_graph(self.vocabulary, ORIGIN), entity_graph(self.entities, ORIGIN)]
        return graphs

    def test_whole_graph_resolves_authority_identities_across_pages(self):
        graphs = self.all_graphs()
        self.assertEqual(validate_global_graph(graphs, origin=ORIGIN), [])
        row = self.by_id['23428974']
        graph = self.graph(row)
        edition = next(n for n in graph['@graph'] if n['@id'] == 'https://doi.org/' + row['doi'])
        self.assertEqual(edition['author']['@id'], entity_uri('dorian-vale', ORIGIN))
        damaged = deepcopy(graphs)
        damaged[0]['@graph'].append({'@type': 'CreativeWork', '@id': ORIGIN + '/items/test#assertion',
                                   'about': {'@id': ORIGIN + '/entities/dorian-vale.html#wrong-entity'}})
        self.assertTrue(any('Undeclared local graph identity' in e for e in validate_global_graph(damaged, origin=ORIGIN)))

    def test_work_only_match_never_becomes_selected_edition_equivalence(self):
        for rid in ('19863790', '19863836', '19863851'):
            record = self.by_id[rid]
            self.assertEqual(institutional_scope(record), 'work')
            page = next(n for n in self.graph(record)['@graph'] if n['@id'] == record['institutional_url'])
            self.assertEqual(page['about']['@id'], work_uri(record, ORIGIN))
        selected = deepcopy(self.by_id['19863790'])
        selected['institutional_metadata']['linked_zenodo_dois'] = [selected['doi']]
        self.assertEqual(institutional_scope(selected), 'exact_edition')
        family = deepcopy(self.by_id['19863790'])
        family['institutional_metadata']['linked_zenodo_dois'] = [family['conceptdoi']]
        self.assertEqual(institutional_scope(family), 'version_family')

    def test_title_level_isbn_is_preserved_without_exporting_format_equivalence(self):
        record = deepcopy(self.by_id['19864099'])
        self.assertTrue(record['isbn'])
        self.assertIsNone(edition_isbn(record))
        edition = next(n for n in self.graph(record)['@graph'] if n['@id'] == 'https://doi.org/' + record['doi'])
        self.assertNotIn('isbn', edition)
        self.assertNotIn('isbn', build_citation_model(record))
        self.assertIn('titleLevelISBN', build_dc(record))
        record['isbn_evidence'] = {'scope': 'edition_format', 'status': 'source_verified',
                                   'source_url': record['zenodo_url'], 'reviewed': '2026-11-04'}
        self.assertEqual(edition_isbn(record), record['isbn'])
        self.assertEqual(build_citation_model(record)['isbn'], record['isbn'])

    def test_source_title_controls_citation_even_when_display_title_differs(self):
        record = deepcopy(self.by_id['19864099'])
        record['title'] = 'Short catalogue label'
        self.assertEqual(build_citation_model(record)['title'], record['source_title'])

    def test_typed_assertions_keep_unknown_reviewer_and_stable_identity(self):
        record = deepcopy(self.by_id['23428974'])
        assertions = typed_relationship_assertions(record, ORIGIN)
        self.assertTrue(assertions)
        self.assertTrue(all(a['source_url'] and a['predicate'] for a in assertions))
        self.assertIn('reviewer', assertions[0]['unknowns'])
        self.assertIsNone(assertions[0]['reviewer'])
        record['institutional_metadata']['reviewed'] = '2026-11-05'
        self.assertEqual([a['id'] for a in assertions], [a['id'] for a in typed_relationship_assertions(record, ORIGIN)])
        record['entity_links'][0]['relation'] = 'endorsed by'
        with self.assertRaisesRegex(ValueError, 'Unregistered'):
            typed_relationship_assertions(record, ORIGIN)

    def test_profile_rejects_date_scope_and_assertion_drift(self):
        self.assertEqual(validate_metadata_profile(self.records, ORIGIN), [])
        record = deepcopy(self.by_id['19863790'])
        record['date'] = '2026-02-31'
        record['institutional_match_scope'] = 'exact_edition'
        record['entity_links'][0]['note'] = 'Changed evidence note'
        errors = validate_metadata_profile([record], ORIGIN)
        self.assertTrue(any('date' in e for e in errors))
        self.assertTrue(any('scope' in e for e in errors))
        self.assertTrue(any('cached relationship' in e for e in errors))

    def test_description_events_are_idempotent_and_do_not_invent_creation(self):
        self.assertEqual(self.records, prepare_metadata_records(self.records, ORIGIN))
        for record in self.records:
            self.assertFalse(record.get('record_created'))
            expected_event = 'rai-accession-2026-11-10' if record['id'] in {'24088563','24088574','24088573'} else 'metadata-profile-3.0-2026-11-04'
            if record['id'] in {'24095308', '24095953'}:
                expected_event = 'working-paper-accession-' + record['id']
            if record['id'] == '24130993':
                expected_event = 'research-dialogue-accession-24130993'
            events = [e for e in record['description_history'] if e.get('event_id') == expected_event]
            self.assertEqual(len(events), 1)
            latest = max(e['date'] for e in record['description_history'] if e.get('date'))
            expected = {e['event_id'] for e in record['description_history'] if e.get('date') == latest}
            self.assertEqual(record['record_modified'], latest)
            self.assertEqual(set(record['record_modified_provenance']['event_ids']), expected)

    def test_combined_graph_preserves_vocabulary_context_and_statement_union(self):
        graphs = self.all_graphs()
        combined = combine_graphs(graphs)
        self.assertEqual(validate_global_graph([combined], origin=ORIGIN), [])
        self.assertTrue(any(isinstance(c, dict) and 'skos' in c for c in combined['@context']))
        ids = [n['@id'] for n in combined['@graph']]
        self.assertEqual(len(ids), len(set(ids)))

    def test_export_agreement_catches_changed_citation_and_scope(self):
        record = self.by_id['19863790']
        rid = record['id']
        model = build_citation_model(record, catalogue_url=ORIGIN + '/items/' + rid + '.html', pdf_url=ORIGIN + '/items/' + rid + '.pdf')
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory)
            (out / 'metadata').mkdir()
            (out / 'items').mkdir()
            (out / 'metadata' / (rid + '.csl.json')).write_text(json.dumps(csl_json(model)))
            (out / 'metadata' / (rid + '.bib')).write_text(bibtex(model))
            (out / 'metadata' / (rid + '.ris')).write_text(ris(model))
            (out / 'metadata' / (rid + '.jsonld')).write_text(json.dumps(self.graph(record)))
            tags = ''.join('<meta name="' + k + '" content="' + escape(v, quote=True) + '">' for k, v in scholar_meta(model))
            (out / 'items' / (rid + '.html')).write_text(tags)
            self.assertEqual(validate_export_agreement([record], out, ORIGIN), [])
            wrong = csl_json(model)
            wrong['DOI'] = '10.5281/zenodo.WRONG'
            (out / 'metadata' / (rid + '.csl.json')).write_text(json.dumps(wrong))
            self.assertTrue(any('citation export disagrees' in e for e in validate_export_agreement([record], out, ORIGIN)))

    def test_quality_is_dimensional_and_missing_checks_are_explicit(self):
        report = build_quality_report(self.records, self.all_graphs(), origin=ORIGIN)
        require_valid_report(report)
        self.assertEqual(len(report['dimensions']['local_creation_date_unknown']), len(self.records))
        self.assertEqual(len(report['dimensions']['title_level_isbn_format_unresolved']), 4)
        self.assertFalse(report['checks']['citation_exports']['executed'])
        self.assertNotIn('completeness_score', report)


if __name__ == '__main__':
    unittest.main()
