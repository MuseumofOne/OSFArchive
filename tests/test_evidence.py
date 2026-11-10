import copy,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from evidence import prepare_evidence,evidence_discovery,build_evidence_pages
ORIGIN='https://archive.museumofone.art'
class EvidenceRecords(unittest.TestCase):
 def setUp(self):self.raw=json.loads((ROOT/'data/evidence.json').read_text())
 def test_published_pages_and_locator_only_sources_remain_distinct(self):
  p=prepare_evidence(self.raw,ORIGIN);self.assertEqual(len(p['documents']),5);self.assertEqual(len(p['claims']),4)
  self.assertEqual(sum(bool(x.get('image')) for d in p['documents'] for x in d['pages']),3)
  self.assertFalse(any(x['id']=='pdf-page-07' for d in p['documents'] for x in d['pages']))
  self.assertFalse((ROOT/'assets/rai-archive/rai-documentary-supplement-v1-p07.png').exists())
  self.assertFalse((ROOT/'dist/assets/rai-archive/rai-documentary-supplement-v1-p07.png').exists())
  for d in p['documents']:
   if d['materialType']=='source-locator':self.assertTrue(all(x.get('image') is None and x.get('transcription') is None for x in d['pages']))
   self.assertTrue(d['recordUrl'].startswith(ORIGIN+'/evidence/'));self.assertEqual(d['provenance'],next(x for x in self.raw['documents'] if x['id']==d['id'])['provenance'])
 def test_release_and_image_permission_fail_closed(self):
  for mutate in [lambda p:p.pop('publication'),lambda p:p['publication'].update(privacyReviewed=False),lambda p:p['documents'][0].update(private=True),lambda p:p['documents'][0]['rights'].update(imagesApproved=False),lambda p:p['documents'][0]['rights'].update(transcriptionApproved=False)]:
   p=copy.deepcopy(self.raw);mutate(p)
   with self.assertRaises(ValueError):prepare_evidence(p,ORIGIN)
 def test_unapproved_reading_layers_and_nested_private_claims_rejected(self):
  for key in ('translation','commentary'):
   p=copy.deepcopy(self.raw);p['documents'][0]['pages'][0][key]={'by':'Editor','status':'reviewed','text':'Unapproved reading'}
   with self.assertRaisesRegex(ValueError,'permission'):prepare_evidence(p,ORIGIN)
  for marker in ({'private':True},{'draft':True},{'visibility':'private'},{'status':'draft'}):
   p=copy.deepcopy(self.raw);p['claims'][0]['nestedReview']=marker
   with self.assertRaisesRegex(ValueError,'Nonpublic'):prepare_evidence(p,ORIGIN)
 def test_claim_identity_and_exact_links_are_validated(self):
  for mutate in [lambda p:p['claims'].append(copy.deepcopy(p['claims'][0])),lambda p:p['claims'][0]['support'][0].update(passageId='missing'),lambda p:p['claims'][0]['support'][0].update(url='https://example.org/unrelated'),lambda p:p['claims'][0]['support'][0].update(sourceId='different-source')]:
   p=copy.deepcopy(self.raw);mutate(p)
   with self.assertRaises(ValueError):prepare_evidence(p,ORIGIN)
 def test_dangling_hierarchy_and_claim_pages_rejected(self):
  for mutate in [lambda p:p['documents'][0].update(collectionId='missing'),lambda p:p['claims'][0]['support'][0].update(pageId='missing'),lambda p:p['documents'][0]['pages'].append(copy.deepcopy(p['documents'][0]['pages'][0]))]:
   p=copy.deepcopy(self.raw);mutate(p)
   with self.assertRaises(ValueError):prepare_evidence(p,ORIGIN)
 def test_source_provenance_and_facets_remain_searchable(self):
  p=prepare_evidence(self.raw,ORIGIN);rows=evidence_discovery(p,ORIGIN)
  self.assertEqual(len(rows),14);self.assertEqual(len({r['id'] for r in rows}),14)
  d=next(r for r in rows if r['id']=='evidence:rai-main-paper-v1');self.assertEqual(d['source_layer'],'research-document');self.assertIn('ko',d['languages']);self.assertIn('24088563',d['relationships'][-1]['target_id'])
 def test_static_records_preserve_readings_rights_provenance_and_exports(self):
  p=prepare_evidence(self.raw,ORIGIN);out={}
  def layout(title,desc,content,path,**kwargs):return '<html><head></head><body>'+content+'</body></html>'
  paths=build_evidence_pages(p,out.__setitem__,layout,ORIGIN)
  self.assertIn('dossiers/park-suk-won-chronology.html',paths)
  for d in p['documents']:
   page=out['evidence/'+d['id']+'.html'];self.assertIn(d['rights']['statement'].split('.')[0],page)
   for x in d['pages']:self.assertIn('id="'+x['id']+'"',page)
   self.assertIn('metadata/evidence/'+d['id']+'.csl.json',out)
  self.assertIn('iiif/rai-main-paper-v1/manifest.json',out);self.assertNotIn('iiif/mmca-collection-07912/manifest.json',out)
  dossier=out['dossiers/park-suk-won-chronology.html']
  for c in p['claims']:self.assertIn('id="'+c['id']+'"',dossier)
if __name__=='__main__':unittest.main()
