"""Regression checks for source/edition metadata boundaries. No network access."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from enrich import enrich_record, date_precision, isbn_details
from metadata import CAT, DCT, build_assertions, build_graph, build_dc


class MetadataBoundaries(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records=json.loads((ROOT/'data/catalogue.json').read_text())
        cls.by_id={str(record['id']):record for record in cls.records}
        cls.authorities=json.loads((ROOT/'data/authorities.json').read_text())

    def enrich(self, record):
        return enrich_record(record,self.authorities)

    def graph(self, record):
        result=build_graph(record,'https://archive.example/items/'+record['id']+'.html','https://archive.example')
        return {node['@id']:node for node in result['@graph']}

    def test_manual_does_not_inherit_another_books_isbn(self):
        record=deepcopy(self.by_id['20100136'])
        record['isbn']='978-1-06-982030-3'  # The earlier normalizer picked Volume I.
        result=self.enrich(record)
        self.assertIsNone(result['isbn'])
        self.assertEqual(result['isbn_applicability'],'unverified')
        self.assertTrue(any(x['value']=='978-1-06-982030-3' for x in result['source_identifiers']))
        edition=self.graph(result)['https://doi.org/'+result['doi']]
        self.assertNotIn('isbn',edition)
        self.assertFalse(any(x['field']=='isbn' for x in build_assertions(result)))

    def test_date_precision_is_preserved_in_export(self):
        for value,precision in [('2025','year'),('2026-04','month'),('2026-05-18','day')]:
            with self.subTest(value=value):
                record=deepcopy(self.records[0]);record['date']=value
                result=self.enrich(record)
                self.assertEqual(result['date'],value)
                self.assertEqual(result['date_precision'],precision)
                self.assertEqual(self.graph(result)['https://doi.org/'+result['doi']]['datePublished'],value)
        self.assertEqual(date_precision('2026-02-31'),'invalid_date')

    def test_enrichment_is_idempotent_and_preserves_snapshot_fields(self):
        for raw in self.records:
            with self.subTest(record=raw['id']):
                once=self.enrich(raw)
                self.assertEqual(once,self.enrich(once))
                for field in ('id','doi','source_title','date','source_description_html','source_created','source_modified'):
                    self.assertEqual(once.get(field),raw.get(field))
                source=ROOT/'data/source'/(raw['id']+'.json')
                before=source.read_bytes();self.enrich(raw);self.assertEqual(source.read_bytes(),before)

    def test_serial_requires_an_explicit_source_relationship(self):
        record=deepcopy(self.by_id['19864115'])
        record['related_identifiers']=[]
        record['keywords']=['ISSN 2819-7232','Journal of Post-Interpretive Criticism']
        result=self.enrich(record)
        self.assertIsNone(result['serial'])
        self.assertFalse(any(node['@type']=='Periodical' for node in self.graph(result).values()))
        record['related_identifiers']=[{'scheme':'issn','identifier':'2819-7232','relation':'isPartOf'}]
        result=self.enrich(record)
        self.assertEqual(result['serial']['source_relation'],'isPartOf')
        self.assertTrue(any(node['@type']=='Periodical' for node in self.graph(result).values()))

    def test_roles_keep_organizations_and_unknown_creator_roles_distinct(self):
        record=deepcopy(self.records[0])
        record['creators']=[{'name':'Vale, Dorian'}]
        record['source_contributors']=[{'name':'Museum of One','type':'HostingInstitution'}]
        result=self.enrich(record)
        self.assertIsNone(result['contributor_roles'][0]['source_role'])
        self.assertEqual(result['contributor_roles'][0]['role_label'],'Creator (role not supplied)')
        nodes=self.graph(result)
        role=next(node for node in nodes.values() if node['@type']=='Role')
        self.assertEqual(role['roleName'],'HostingInstitution')
        self.assertEqual(nodes[role['contributor']['@id']]['@type'],'Organization')

    def test_new_fields_keep_provenance_and_export_scope(self):
        record=self.enrich(self.by_id['19864099'])
        fields={item['field']:item for item in build_assertions(record)}
        for field in ('date_precision','digital_extent','alternate_titles','identifier_validation','contributor_roles','authority_links','edition_statement'):
            if record.get(field):
                self.assertIn(field,fields)
                self.assertTrue(fields[field].get('source_url'))
        self.assertEqual(fields['digital_extent']['status'],'derived_from_source')
        self.assertEqual(fields['identifier_validation']['status'],'local_syntax_validation')
        self.assertTrue(any(field.startswith('research_programme:') for field in fields))
        ET.fromstring(build_dc(record))
        self.assertTrue(any(node['@type']=='BreadcrumbList' for node in self.graph(record).values()))

    def test_identifier_checks_do_not_promote_registry_claims(self):
        self.assertTrue(isbn_details('978-1-0698203-0-3')['checksum_valid'])
        self.assertFalse(isbn_details('978-1-0698203-0-0')['checksum_valid'])
        result=self.enrich(self.records[0])
        self.assertTrue(result['identifier_validation']['orcid']['checksum_valid'])
        self.assertIn('not a live registry verification',result['identifier_validation']['orcid']['note'])

    def test_review_repository_and_local_lifecycle_dates_remain_separate(self):
        record=self.enrich(self.by_id['19864099'])
        record['date']='2026-04'  # Edition date precision must remain unchanged.
        record['source_review']='2026-11-04'
        for key in ('record_created','record_modified'):
            record.pop(key,None)
        nodes=self.graph(record)
        catalogue=next(node for node in nodes.values() if node['@id'].endswith('#catalogue-record'))
        page=next(node for node in nodes.values() if node['@id'].endswith('#webpage'))
        source=nodes[record['zenodo_url']]
        edition=nodes['https://doi.org/'+record['doi']]
        self.assertNotIn('dateCreated',catalogue)
        self.assertNotIn('dateModified',catalogue)
        self.assertEqual(page['lastReviewed'],'2026-11-04')
        self.assertEqual(source['dateCreated'],record['source_created'])
        self.assertEqual(source['dateModified'],record['source_modified'])
        self.assertEqual(edition['datePublished'],'2026-04')
        self.assertNotIn('dateCreated',edition)
        self.assertNotIn('dateModified',edition)
        record['record_created']='2026-11-02'
        record['record_modified']='2026-11-03'
        nodes=self.graph(record)
        catalogue=next(node for node in nodes.values() if node['@id'].endswith('#catalogue-record'))
        self.assertEqual(catalogue['dateCreated'],'2026-11-02')
        self.assertEqual(catalogue['dateModified'],'2026-11-03')
        xml=ET.fromstring(build_dc(record))
        self.assertEqual(xml.findtext('{'+DCT+'}issued'),'2026-04')
        self.assertIsNone(xml.find('{'+DCT+'}created'))
        self.assertIsNone(xml.find('{'+DCT+'}modified'))
        for term,field in [('repositoryRecordCreated','source_created'),('repositoryRecordModified','source_modified'),('recordCreated','record_created'),('recordModified','record_modified'),('sourceReviewDate','source_review')]:
            self.assertEqual(xml.findtext('{'+CAT+'}'+term),record[field])
        assertions={item['field']:item for item in build_assertions(record)}
        self.assertEqual(assertions['record_created']['status'],'local_catalogue_lifecycle')
        self.assertEqual(assertions['source_review']['status'],'catalogue_source_review')


if __name__=='__main__':
    unittest.main()
