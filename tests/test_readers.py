"""Release checks for byte identity, reader contracts and local access copies."""
import hashlib,json,re,unittest
from pathlib import Path
from html.parser import HTMLParser
ROOT=Path(__file__).resolve().parents[1];DIST=ROOT/'dist'
class Contract(HTMLParser):
 def __init__(self,text):super().__init__();self.ids=[];self.body={};self.feed(text)
 def handle_starttag(self,t,a):
  a=dict(a)
  if a.get('id'):self.ids.append(a['id'])
  if t=='body':self.body=a
class ReadingCopies(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.copies=json.loads((ROOT/'data/readers.json').read_text())
 def test_copies_match_source_and_access_checksums(self):
  for r in self.copies:
   with self.subTest(id=r['id']):
    b=(DIST/'assets/documents'/(r['id']+'.pdf')).read_bytes();self.assertTrue(b.startswith(b'%PDF-'));self.assertEqual(len(b),r['bytes']);self.assertEqual('md5:'+hashlib.md5(b).hexdigest(),r['checksum']);self.assertEqual(hashlib.sha256(b).hexdigest(),r['sha256'])
    source=json.loads((ROOT/'data/source'/(r['id']+'.json')).read_text());self.assertTrue(any(f.get('checksum')==r['checksum'] for f in source['files']))
 def test_reader_pages_have_complete_controls_and_correct_roots(self):
  needed=['book-reader','reader-title','reader-stage','reader-pages','reader-status','reader-prev','reader-next','reader-zoom-out','reader-zoom-in','reader-fit','reader-fullscreen','reader-thumbs-toggle','reader-page','reader-total','reader-mode','reader-progress','reader-thumbnails','reader-thumb-list','reader-fallback','reader-loading']
  for r in self.copies:
   with self.subTest(id=r['id']):
    p=Contract((DIST/'read'/(r['id']+'.html')).read_text());self.assertEqual(p.body['data-root'],'../');self.assertEqual(len(p.ids),len(set(p.ids)))
    for id in needed:self.assertIn(id,p.ids)
    manifest=json.loads((DIST/'metadata/readers'/(r['id']+'.json')).read_text());self.assertEqual(manifest['pdf_url'],'../assets/documents/'+r['id']+'.pdf')
 def test_reader_rights_separator_does_not_duplicate_existing_punctuation(self):
  import sys,copy
  sys.path.insert(0,str(ROOT/'scripts'))
  from readers import build_reader_pages
  source=json.loads((ROOT/'data/catalogue.json').read_text())[0]
  source['reading_copy']=self.copies[0]
  for rights in ('In Copyright','In Copyright.'):
   with self.subTest(rights=rights):
    record=copy.deepcopy(source);record['license']={'label':rights};pages={}
    build_reader_pages([record],lambda path,text:pages.update({path:text}),lambda title,description,content,*a,**kw:content,'https://archive.museumofone.art')
    rendered=pages['read/'+record['id']+'.html']
    self.assertIn('In Copyright. Original file retained unchanged',rendered)
    self.assertNotIn('In Copyright..',rendered)
    self.assertEqual(record['license']['label'],rights)
 def test_metadata_distinguishes_local_copy_from_deposited_edition(self):
  for r in self.copies:
   data=json.loads((DIST/'metadata'/(r['id']+'.json')).read_text());self.assertEqual(data['reading_copy']['sha256'],r['sha256']);self.assertEqual(data['page_count'],r['page_count']);self.assertTrue(any(a['field']=='reading_copy' and a['status']=='derived_file_inspection' for a in data['field_assertions']))
   graph=json.loads((DIST/'metadata'/(r['id']+'.jsonld')).read_text())['@graph'];copy=next(n for n in graph if n.get('@type')=='MediaObject' and '/assets/documents/' in n['@id']);self.assertEqual(copy['identifier']['value'],r['sha256']);self.assertNotEqual(copy['@id'],copy['encodesCreativeWork']['@id'])
 def test_vendored_engine_worker_and_licence_are_present(self):
  vendor=DIST/'assets/vendor/pdfjs';version=json.loads((vendor/'VERSION.json').read_text())['version'];self.assertIn(version,(vendor/'pdf.mjs').read_text());self.assertIn(version,(vendor/'pdf.worker.mjs').read_text());self.assertIn('Apache',(vendor/'LICENSE').read_text());self.assertTrue((vendor/'wasm').is_dir());self.assertTrue((vendor/'standard_fonts').is_dir())
if __name__=='__main__':unittest.main()
