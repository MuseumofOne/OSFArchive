"""Source preservation, truthful unknowns and usable institutional policy pages."""
import copy
import json
from pathlib import Path
import sys
import unittest
from urllib.parse import parse_qs, urlparse
from html.parser import HTMLParser

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from policies import attach_catalogue_history, build_policy_pages, policy_record_panel


class Links(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.links = []
        self.tags = []
        self.ids = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        self.tags.append(tag)
        if tag == 'a':
            self.links.append(values.get('href', ''))
        if values.get('id'):
            self.ids.append(values['id'])


class Policies(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records = json.loads((ROOT / 'data/catalogue.json').read_text())
        cls.manifests = {m['id']: m for m in json.loads((ROOT / 'data/readers.json').read_text())}

    def test_additive_context_preserves_original_metadata(self):
        original = copy.deepcopy(self.records)
        enriched = attach_catalogue_history(self.records)
        self.assertEqual(self.records, original)
        for old, new in zip(original, enriched):
            for field, value in old.items():
                self.assertEqual(new[field], value, field)
            context = new['archival_context']
            self.assertEqual(context['source_metadata_retrieved'], old['provenance']['retrieved'])
            self.assertEqual(context['source_snapshot'], old['provenance']['source_snapshot'])
            self.assertEqual(context['source_filenames'], [f['name'] for f in old['files']])
            self.assertEqual(context['source_repository']['record_url'], old['zenodo_url'])
            self.assertEqual(context['custodial_history']['status'], 'not_documented')
            self.assertEqual(context['original_order']['status'], 'not_documented')
            manifest = self.manifests[old['id']]
            self.assertEqual(context['access_copy']['source_filename'], manifest['source_filename'])
            self.assertEqual(context['access_copy']['verified_at'], manifest['verified_at'])
            self.assertEqual(context['access_copy']['sha256'], manifest['sha256'])

    def test_unknowns_are_not_fabricated(self):
        record = {'id': 'unknown-test', 'title': 'Untitled test record'}
        result = attach_catalogue_history([record])[0]
        context = result['archival_context']
        self.assertIsNone(context['source_metadata_retrieved'])
        self.assertEqual(context['source_metadata_retrieval_status'], 'Not documented')
        self.assertEqual(context['source_repository']['name'], 'Not documented')
        self.assertEqual(context['source_filenames'], [])
        self.assertNotIn('verified_at', context['access_copy'])
        self.assertEqual(result['description_history'], [])
        self.assertNotIn('record_modified', result)

    def test_repeated_builds_preserve_history_without_duplicates(self):
        enriched = attach_catalogue_history(self.records)
        self.assertEqual(attach_catalogue_history(enriched), enriched)
        prior = copy.deepcopy(enriched[:1])
        old_event = {'event_id': 'recorded-earlier-revision', 'date': '2026-11-03', 'action': 'User-supplied prior record event'}
        prior[0]['description_history'].insert(0, old_event)
        current = attach_catalogue_history(self.records[:1], prior)[0]
        self.assertEqual(current['description_history'][0], old_event)
        self.assertEqual(len({e['event_id'] for e in current['description_history']}), len(current['description_history']))
        for event in current['description_history'][1:]:
            self.assertEqual(event['responsible_service'], 'Museum of One')
            self.assertNotIn('curator', event)
            self.assertIn('date_kind', event)

    def test_public_pages_provide_real_contact_and_no_fake_submission(self):
        files = {}
        records = attach_catalogue_history(self.records)
        def layout(title, desc, content, path, **kwargs):
            return '<html><head><title>' + title + '</title></head><body>' + content + '</body></html>'
        pages = build_policy_pages(records, files.__setitem__, layout, 'https://archive.example')
        self.assertEqual(pages, ['policies.html', 'research-help.html'])
        for path in pages:
            parsed = Links(files[path])
            self.assertNotIn('form', parsed.tags)
            self.assertEqual(len(parsed.ids), len(set(parsed.ids)))
            mail = [urlparse(u) for u in parsed.links if u.startswith('mailto:')]
            self.assertTrue(any(u.path == 'research@museumofone.art' for u in mail))
            subjects = [parse_qs(u.query).get('subject', [''])[0].lower() for u in mail]
            self.assertTrue(any('correction' in s for s in subjects))
            self.assertTrue(any('research enquiry' in s for s in subjects))
        exported = json.loads(files['metadata/policies.json'])
        self.assertEqual(exported['catalogue_record_count'], len(records))
        self.assertEqual(exported['catalogue_snapshot_date'], '2026-11-04')
        self.assertIn('not a live', files['policies.html'])
        self.assertIn('automated drafting', files['policies.html'])
        histories = json.loads(files['metadata/description-history.json'])
        self.assertEqual(histories[0]['description_history'], records[0]['description_history'])

    def test_record_panel_displays_context_history_and_encoded_correction(self):
        record = attach_catalogue_history(self.records[:1])[0]
        html = policy_record_panel(record)
        self.assertIn('Description history &amp; responsibility', html)
        self.assertIn('Source-based automated description assistance', html)
        self.assertIn(record['files'][0]['name'], html)
        self.assertIn('href="../policies.html"', html)
        links = Links(html).links
        query = next(parse_qs(urlparse(link).query) for link in links if link.startswith('mailto:'))
        self.assertIn(record['accession'], query['subject'][0])
        self.assertIn(record['doi'], query['body'][0])

    def test_lifecycle_comes_from_documented_local_events_not_source_dates(self):
        record = copy.deepcopy(self.records[0])
        record['source_created'] = '2000-01-01T12:00:00Z'
        record['source_modified'] = '2099-12-31T12:00:00Z'
        record['source_review'] = '2099-12-30'
        record['description_history'] = [
            {'event_id': 'invalid-day', 'date': '2099-02-31'},
            {'event_id': 'partial-day', 'date': '2099-12'},
            {'event_id': 'reviewed-correction', 'date': '2026-11-05', 'action': 'Documented catalogue correction'},
        ]
        result = attach_catalogue_history([record])[0]
        self.assertNotIn('record_created',result)
        self.assertEqual(result['record_modified'],'2026-11-05')
        self.assertEqual(result['record_modified_provenance']['event_ids'],['reviewed-correction'])
        self.assertEqual(result['source_modified'],record['source_modified'])
        self.assertEqual(result['source_review'],record['source_review'])
        self.assertIn('Latest documented description event',policy_record_panel(result))
        self.assertEqual(attach_catalogue_history([result])[0],result)
        result['description_history'].append({'event_id':'later-correction','date':'2026-11-06','action':'Later documented catalogue correction'})
        updated=attach_catalogue_history([result])[0]
        self.assertEqual(updated['record_modified'],'2026-11-06')
        self.assertEqual(updated['record_modified_provenance']['event_ids'],['later-correction'])
        record['record_created']='2026-11-01'
        record['record_modified']='2026-11-06'
        explicit=attach_catalogue_history([record])[0]
        self.assertEqual(explicit['record_created'],'2026-11-01')
        self.assertEqual(explicit['record_modified'],'2026-11-06')
        self.assertNotIn('record_modified_provenance',explicit)

    def test_future_record_does_not_inherit_initial_policy_adoption_date(self):
        record = {'id':'future-record', 'title':'A future description',
                  'zenodo_url':'https://zenodo.org/records/99999999',
                  'date_precision':'day', 'provenance':{'retrieved':'2027-03-01'}}
        result = attach_catalogue_history([record])[0]
        self.assertNotIn('record_created', result)
        self.assertNotIn('record_modified', result)
        self.assertFalse(result['description_history'])
        self.assertIsNone(result['archival_context']['catalogue_snapshot_date'])
        record['description_history'] = [{'event_id':'new-description', 'date':'2027-03-02', 'action':'Documented description'}]
        self.assertEqual(attach_catalogue_history([record])[0]['record_modified'], '2027-03-02')


if __name__ == '__main__':
    unittest.main()
