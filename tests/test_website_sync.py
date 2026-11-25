import copy,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from website_sync import PublicContentAPI,reconcile,projection,Readable,FetchFailure,seal,unseal,fetch_collection,digest,encoded
from website_pages import build_website_pages,access_asset,inline_pdf_reader_pages
AT='2026-11-05T12:00:00Z';RID='a'*24
class Fetch:
 def __init__(self,content=b'file'):self.content=content;self.cache={};self.asset_bytes=0
 def get(self,url,limit=0):
  if isinstance(self.content,Exception):raise self.content
  return self.content
class Sync(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
  cls.private=cls.key.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption())
  cls.public=cls.key.public_key().public_bytes(serialization.Encoding.PEM,serialization.PublicFormat.SubjectPublicKeyInfo)
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name);(self.root/'config').mkdir();(self.root/'config/key.pem').write_bytes(self.public)
  self.policy={'public_key':'config/key.pem','max_attachment_bytes':100000,'max_total_asset_bytes':200000};self.work=self.root/'work';self.row={'kind':'post','record':{'id':RID,'title':'تجربة — 考察','url':'https://www.museumofone.art/a/','visibility':'public','status':'published','published_at':'2025-03-02T00:00:00Z','updated_at':'2026-11-05T00:00:00Z','html':'<h2 id="part">An essay</h2><p>“A quote” — تجربة</p>','authors':[{'name':'Credited Writer','email':'private@example.com'}],'tags':[{'name':'Public subject','visibility':'public'},{'name':'#private','visibility':'internal'}],'codeinjection_head':'<meta name="DC.subject" content="A"><meta name="DC.subject" content="A"><meta name="citation_doi" content="10.1234/source">'}}
 def run_sync(self,rows=None,state=None,**kwargs):return reconcile(rows if rows is not None else [self.row],state,self.root,self.work,self.policy,kwargs.pop('fetcher',Fetch()),at=AT,**kwargs)
 def test_dry_plan_exact_and_no_capture_writes(self):
  state,public,r=self.run_sync(dry=True);self.assertEqual(r['eligible_records'],1);self.assertEqual(r['changes'][0]['action'],'missing');self.assertFalse((self.work/'state.json').exists());self.assertFalse((self.work/'vault').exists())
 def test_new_record_unicode_repeated_metadata_and_private_fields(self):
  state,p,r=self.run_sync();self.assertEqual(p[0]['source']['title'],'تجربة — 考察');self.assertEqual(len(p[0]['source']['source_declared_metadata']),3);self.assertEqual(p[0]['source']['subjects'],['Public subject']);self.assertNotIn('private@example.com',encoded(p).decode());self.assertNotIn('html',encoded(state).decode());self.assertEqual(len(state['records']),1)
 def test_repeated_updates_preserve_publication_date_and_revisions(self):
  s,p,r=self.run_sync();s2,p2,r2=self.run_sync(state=s);self.assertEqual(s2['records'][RID]['revisions'],s['records'][RID]['revisions']);self.assertEqual(r2['changes'][0]['action'],'unchanged')
  self.row['record'].update(html='<p>Revised text</p>',published_at='2026-01-01T00:00:00Z',updated_at='2026-11-05T11:00:00Z')
  s3,p3,r3=self.run_sync(state=s2);self.assertEqual(len(s3['records'][RID]['revisions']),2);self.assertEqual(p3[0]['original_published_at'],'2025-03-02T00:00:00Z');self.assertEqual(p3[0]['source']['published_at'],'2026-01-01T00:00:00Z')
 def test_url_change_keeps_stable_archive_and_discovery_ids(self):
  s,p,_=self.run_sync();self.row['record']['url']='https://www.museumofone.art/renamed/';s2,p2,_=self.run_sync(state=s);self.assertEqual(p[0]['archive_id'],p2[0]['archive_id']);self.assertEqual(p[0]['discovery_id'],p2[0]['discovery_id'])
 def test_out_of_order_does_not_downgrade_state(self):
  s,p,_=self.run_sync();before=encoded(s);self.row['record']['updated_at']='2026-11-04T00:00:00Z'
  with self.assertRaises(FetchFailure):self.run_sync(state=s)
  self.assertEqual(encoded(s),before)
 def test_drafts_private_members_future_unknown_visibility_excluded(self):
  for field,value in [('status','draft'),('status','scheduled'),('visibility','members'),('visibility','paid'),('visibility','private'),('visibility',None),('published_at','2099-01-01T00:00:00Z')]:
   with self.subTest(field=field,value=value):
    row=copy.deepcopy(self.row);row['record'][field]=value;s,p,r=self.run_sync([row]);self.assertFalse(p);self.assertNotIn('source_id',str(r['excluded']))
 def test_new_and_revised_pages_refresh_document_language_without_guessing_work_language(self):
  class PublicPage(Fetch):
   def __init__(self):super().__init__();self.calls=[]
   def document_language(self,url):self.calls.append(url);return 'en-GB'
  fetcher=PublicPage()
  state,rows,_=self.run_sync(fetcher=fetcher)
  self.assertEqual(rows[0]['document_language']['language'],'en-GB')
  self.assertIsNone(rows[0]['language'])
  state,_,_=self.run_sync(state=state,fetcher=fetcher)
  self.assertEqual(len(fetcher.calls),1)
  self.row['record']['html']='<p>Updated public text.</p>'
  _,_,_=self.run_sync(state=state,fetcher=fetcher)
  self.assertEqual(len(fetcher.calls),2)
 def test_public_collection_tags_classify_new_pages_and_posts(self):
  from publication_arrangement import classify_capture
  source=dict(self.row['record'],kind='page',subjects=['Theory & Treatises'])
  self.assertEqual(classify_capture(source,{}),('Theory & treatises','Website publication'))
  source.update(kind='post',subjects=['Methodology'])
  self.assertEqual(classify_capture(source,{}),('Methodology','Website publication'))
  source.update(kind='page',subjects=[])
  self.assertEqual(classify_capture(source,{}),(None,'Website reference'))
 def test_published_dialogues_share_the_essays_collection(self):
  from publication_arrangement import classify_capture
  for slug in ('dong-yeon-koh','lu-peng','tomoki-akimaru'):
   with self.subTest(slug=slug):
    source={'url':f'https://www.museumofone.art/{slug}/','kind':'page','subjects':[]}
    self.assertEqual(classify_capture(source,{}),('Essays & research','Website publication'))
 def test_missing_metadata_reported_without_invention(self):
  r=self.row['record'];r['authors']=[];r.pop('updated_at');s,p,report=self.run_sync();self.assertIsNone(p[0]['language']);self.assertIsNone(p[0]['source']['updated_at']);self.assertTrue(report['validation_issues']);self.assertNotIn('bookEdition',encoded(p).decode())
 def test_unpublishing_withholds_copy_and_preserves_encrypted_history(self):
  s,p,_=self.run_sync();s2,p2,r=self.run_sync([],state=s);self.assertFalse(p2);self.assertEqual(s2['records'][RID]['access_status'],'withheld');self.assertEqual(len(s2['records'][RID]['revisions']),1)
  blob=(self.work/s2['records'][RID]['revisions'][0]['vault_path']).read_bytes();original=unseal(blob,self.private,None);self.assertEqual(original['source']['html'],self.row['record']['html']);self.assertNotIn('An essay',blob.decode())
 def test_attachment_capture_error_retry_and_encrypted_file_recovery(self):
  self.row['record']['html']='<p><a href="/content/files/2026/11/a.pdf">PDF</a></p><img src="https://external.example/image.jpg" alt="External image">'
  s,p,r=self.run_sync(fetcher=Fetch(FetchFailure('broken')));self.assertEqual(r['failed_attachments'],1);self.assertEqual(p[0]['attachments'][1]['storage'],'external_link_only')
  b=b'%PDF-1.7 fixture';s2,p2,r2=self.run_sync(state=s,fetcher=Fetch(b));self.assertEqual(r2['failed_attachments'],0);a=p2[0]['attachments'][0];self.assertEqual(a['sha256'],digest(b));self.assertEqual(a['storage'],'local_archival_file')
  recovery=unseal((self.work/'vault/assets'/(digest(b)+'.json')).read_bytes(),self.private,None);import base64;self.assertEqual(base64.b64decode(recovery['bytes_base64']),b)
 def test_duplicate_ids_or_urls_rejected(self):
  with self.assertRaises(FetchFailure):self.run_sync([self.row,self.row])
  other=copy.deepcopy(self.row);other['record']['id']='b'*24
  with self.assertRaises(FetchFailure):self.run_sync([self.row,other])
 def test_active_code_inert_reading_copy_original_retained(self):
  self.row['record']['html']='<p>Before</p><script>alert("unsafe")</script><iframe src="https://external.example/"></iframe><a href="javascript:alert(1)">Link</a><p>After</p>'
  s,p,r=self.run_sync();self.assertNotIn('<script',p[0]['readable_html']);self.assertNotIn('javascript:',p[0]['readable_html']);self.assertIn('After',p[0]['readable_html']);self.assertIn('<script',p[0]['source']['html'])
 def test_latest_capture_uses_original_publication_date(self):
  newer=copy.deepcopy(self.row)
  newer['record'].update(id='f'*24,title='Newly published research',url='https://www.museumofone.art/new/',published_at='2026-10-01T00:00:00Z')
  state,_,_=self.run_sync()
  self.row['record'].update(html='<p>Recent edit to the older work</p>',updated_at='2026-11-05T11:00:00Z')
  self.run_sync([self.row,newer],state=state)
  out=self.root/'dist';out.mkdir()
  def write(path,text):
   file=out/path;file.parent.mkdir(parents=True,exist_ok=True);file.write_text(text)
  build_website_pages(self.work,out,write,lambda title,description,content,*args,**kwargs:content,'https://archive.museumofone.art')
  listing=(out/'website-records.html').read_text()
  self.assertLess(listing.index('Newly published research'),listing.index('تجربة — 考察'))
 def test_capture_title_and_verified_theme_fragment_aliases(self):
  source='https://www.museumofone.art/research-methods/'
  uncaptured='https://www.museumofone.art/another/'
  self.row['record'].update(url=source,html=f'''
   <h2 id="outputs-and-developments">Outputs and developments</h2>
   <h3 id="preparatory-curatorial-micro-study">Preparatory curatorial micro-study</h3>
   <a href="{source}#programme-outputs">Outputs</a>
   <a href="{source}#preparatory-curatorial-study">Study</a>
   <a href="{source}#live-only">Interactive source</a>
   <a href="{uncaptured}#programme-outputs">Uncaptured programme</a>
  ''')
  self.run_sync()
  out=self.root/'dist'
  def write(path,text):
   file=out/path;file.parent.mkdir(parents=True,exist_ok=True);file.write_text(text)
  def layout(title,description,content,*args,**kwargs):return f'<title>{title}</title>{content}'
  origin='https://archive.museumofone.art'
  build_website_pages(self.work,out,write,layout,origin)
  release=f'website/web-{RID}.html'
  page=(out/release).read_text()
  self.assertIn('Website capture (2026-11-05)',page)
  self.assertIn('2025-03-02T00:00:00Z',page)
  self.assertIn(f'href="{origin}/{release}#outputs-and-developments"',page)
  self.assertIn(f'href="{origin}/{release}#preparatory-curatorial-micro-study"',page)
  self.assertIn(f'href="{source}#live-only"',page)
  self.assertIn(f'href="{uncaptured}#programme-outputs"',page)
  self.assertIn(f'href="{source}#programme-outputs"',(out/f'website/web-{RID}.source.html.txt').read_text())
 def test_research_programmes_labels_only_two_unmarked_heading_phrases(self):
  korean='<h3 id="korean-art">Korean experimental art · 한국 실험미술</h3>'
  japanese='<h3 id="japanese-art">Postwar Japanese art · 戦後日本美術</h3>'
  marked='<h3 lang="en">Postwar Japanese art · <span lang="ja">戦後日本美術</span></h3>'
  body=korean+japanese+marked+'<p>한국 실험미술 and 戦後日本美術</p>'
  other=copy.deepcopy(self.row)
  other['record'].update(id='d'*24,html=body)
  self.row['record'].update(url='https://www.museumofone.art/research-programmes/',html=body)
  self.row['kind']='page'
  _,captures,_=self.run_sync([self.row,other])
  out=self.root/'dist'
  def write(path,text):
   file=out/path
   file.parent.mkdir(parents=True,exist_ok=True)
   file.write_text(text)
  build_website_pages(self.work,out,write,lambda title,description,body,*args,**kw:body,
                      'https://archive.museumofone.art')
  programme=(out/f'website/web-{RID}.html').read_text()
  self.assertIn(korean.replace('한국 실험미술','<span lang="ko">한국 실험미술</span>'),programme)
  self.assertIn(japanese.replace('戦後日本美術','<span lang="ja">戦後日本美術</span>'),programme)
  self.assertIn(marked,programme)
  self.assertIn('<p>한국 실험미술 and 戦後日本美術</p>',programme)
  unrelated=(out/('website/web-'+'d'*24+'.html')).read_text()
  self.assertIn(korean+japanese,unrelated)
  archived=(out/f'website/web-{RID}.source.html.txt').read_text()
  self.assertEqual(archived,body)
  generated=json.loads((out/'metadata/website-captures.json').read_text())
  self.assertEqual({r['archive_id']:r['capture']['content_hash'] for r in generated},
                   {r['archive_id']:r['capture']['content_hash'] for r in captures})

 def test_bilingual_summaries_and_link_labels_keep_source_fixity(self):
  h2='<h2 id="korean-summary">한국어 연구 개요</h2>'
  h2_marked='<h2 lang="ko">한국어 연구 개요</h2>'
  opener='이 워킹페이퍼는 김용익, 박석원, 이강소, 김구림의 작품에 관한 기록을 비교한다.'
  body=h2+h2_marked+f'<p>{opener}</p><p>Japanese art history (日本美術史).</p>'
  body+='<p><a href="https://critique.aicajapan.com/19740">Japanese edition (日本語)</a></p>'
  slugs=('titles-dates-and-reconstructed-works','rai-identity-chronology-korean-experimental-art',
         'rai-documentary-supplement','rai-extended-case-studies','research-programmes','tomoki-akimaru','another')
  rows=[]
  for i,slug in enumerate(slugs):
   row=copy.deepcopy(self.row)
   row['record'].update(id=f'{i:024x}',url=f'https://www.museumofone.art/{slug}/',html=body)
   rows.append(row)
  self.run_sync(rows)
  out=self.root/'dist'
  def write(path,text):
   file=out/path
   file.parent.mkdir(parents=True,exist_ok=True)
   file.write_text(text)
  build_website_pages(self.work,out,write,lambda title,description,body,*args,**kw:body,
                      'https://archive.museumofone.art')
  for i,slug in enumerate(slugs):
   with self.subTest(slug=slug):
    rendered=(out/f'website/web-{i:024x}.html').read_text()
    self.assertEqual('<h2 id="korean-summary" lang="ko">한국어 연구 개요</h2>' in rendered,i<4)
    self.assertIn(h2_marked,rendered)
    self.assertEqual(f'<p lang="ko">{opener}</p>' in rendered,i==0)
    self.assertEqual('(<span lang="ja">日本美術史</span>)' in rendered,slug=='research-programmes')
    self.assertEqual('(<span lang="ja">日本語</span>)</a>' in rendered,slug=='tomoki-akimaru')
    self.assertEqual((out/f'website/web-{i:024x}.source.html.txt').read_text(),body)

 def test_editorial_subjects_and_reviewed_doi_keep_source_fixity(self):
  doi_source='https://www.museumofone.art/formal-defence-of-post-interpretive-criticism/'
  doi='10.5281/zenodo.16934437'
  self.row['record'].update(url=doi_source,tags=[],codeinjection_head='')
  dialogue=copy.deepcopy(self.row)
  dialogue['record'].update(id='d'*24,url='https://www.museumofone.art/lu-peng/',title='Lü Peng')
  dialogue['kind']='page'
  _,captures,_=self.run_sync([self.row,dialogue])
  out=self.root/'dist'
  def write(path,text):
   file=out/path
   file.parent.mkdir(parents=True,exist_ok=True)
   file.write_text(text)
  build_website_pages(self.work,out,write,lambda title,description,body,*args,**kw:body,
                      'https://archive.museumofone.art')
  result=json.loads((out/'metadata/website-captures.json').read_text())
  by_source={row['source']['url']:row for row in result}
  reviewed=by_source[doi_source]
  self.assertEqual(reviewed['source']['source_declared_metadata'],[])
  self.assertEqual(reviewed['arrangement']['related_publication_doi']['doi'],doi)
  page=(out/f'website/web-{RID}.html').read_text()
  self.assertIn(f'href="https://doi.org/{doi}"',page)
  self.assertIn(f'href="https://api.datacite.org/dois/{doi}"',page)
  self.assertIn('Related publication’s deposited version DOI',page)
  for capture in captures:
   result=by_source[capture['source']['url']]
   self.assertEqual(result['capture']['content_hash'],capture['capture']['content_hash'])
   original=out/f"website/{capture['archive_id']}.source.html.txt"
   self.assertEqual(original.read_text(),capture['source']['html'])
  lu=by_source[dialogue['record']['url']]['arrangement']
  self.assertEqual(lu['source_subjects'],[])
  self.assertEqual(lu['editorial_subjects'],
                   ['Chinese art historiography','Post-Interpretive Criticism','Research dialogue'])
  self.assertNotIn('related_publication_doi',lu)

 def test_same_day_same_title_captures_keep_both_publication_dates(self):
  other=copy.deepcopy(self.row)
  other['record'].update(id='d'*24,url='https://www.museumofone.art/another/',
                         published_at='2025-04-02T00:00:00Z')
  self.run_sync([self.row,other])
  out=self.root/'dist'
  def write(path,text):
   file=out/path;file.parent.mkdir(parents=True,exist_ok=True);file.write_text(text)
  def layout(title,description,content,*args,**kwargs):return f'<title>{title}</title>{content}'
  build_website_pages(self.work,out,write,layout,'https://archive.museumofone.art')
  first=(out/f'website/web-{RID}.html').read_text()
  second=(out/('website/web-'+'d'*24+'.html')).read_text()
  self.assertIn('Website capture (2026-11-05, source published 2025-03-02)',first)
  self.assertIn('Website capture (2026-11-05, source published 2025-04-02)',second)
 def test_curated_files_never_mutated_and_withdrawn_render_paths_removed(self):
  (self.root/'data').mkdir();curated=self.root/'data/catalogue.json';curated.write_text('{"manual":"retain"}');before=curated.read_bytes();s,p,_=self.run_sync();out=self.root/'dist';out.mkdir()
  def write(path,text):f=out/path;f.parent.mkdir(parents=True,exist_ok=True);f.write_text(text)
  def layout(title,description,body,*args,**kw):return body
  paths=build_website_pages(self.work,out,write,layout,'https://archive.museumofone.art');self.assertTrue((out/'website'/('web-'+RID+'.html')).exists())
  self.run_sync([],state=s);build_website_pages(self.work,out,write,layout,'https://archive.museumofone.art');self.assertFalse((out/'website'/('web-'+RID+'.html')).exists());self.assertEqual(curated.read_bytes(),before)
 def test_obsolete_uploaded_citations_have_qualified_access_derivative(self):
  raw=encoded([{'title':'Exact title','DOI':'10.1234/exact','custom':{'related-records':['https://museumofone.omeka.net/items/show/81']}}]);file=self.root/'citations.json';file.write_bytes(raw);out=self.root/'out'
  a,n=access_asset({'archive_path':'assets/website-captures/'+digest(raw)+'.json','sha256':digest(raw),'bytes':len(raw)},file,out,'https://archive.museumofone.art',[{'id':'123','title':'Exact title','doi':'10.1234/exact'}])
  self.assertEqual(n,1);self.assertEqual(file.read_bytes(),raw);self.assertEqual(a['source_sha256'],digest(raw));self.assertTrue(a['access_derivative']);self.assertNotEqual(a['sha256'],a['source_sha256'])
  public=(out/a['archive_path']).read_bytes();self.assertEqual(digest(public),a['sha256']);self.assertNotIn(b'museumofone.omeka.net',public);self.assertIn(b'https://archive.museumofone.art/items/123.html',public)
 def test_unmapped_obsolete_uploaded_links_are_not_published(self):
  raw=encoded([{'title':'Unknown work','DOI':'10.1234/unknown','url':'https://museumofone.omeka.net/items/show/999'}]);file=self.root/'citations.json';file.write_bytes(raw);out=self.root/'out'
  a,n=access_asset({'archive_path':'assets/website-captures/'+digest(raw)+'.json','sha256':digest(raw),'bytes':len(raw)},file,out,'https://archive.museumofone.art',[])
  self.assertEqual(a['storage'],'encrypted_recovery_only');self.assertNotIn('archive_path',a);self.assertFalse(out.exists());self.assertEqual(file.read_bytes(),raw)
 def test_cipher_authentication_and_wrong_key(self):
  b=seal({'text':'آرشيف'},self.public);self.assertEqual(unseal(b,self.private,None),{'text':'آرشيف'});j=json.loads(b);j['ciphertext']=j['ciphertext'][:-4]+'AAAA'
  with self.assertRaises(Exception):unseal(encoded(j),self.private,None)
 def test_full_pagination_for_posts_and_pages(self):
  class API:
   def get(self,url,*args):
    from urllib.parse import urlsplit,parse_qs
    if url.endswith('.art/'):
     return (
         b'<script>var demo={contentKey:"example-placeholder"}</script>'
         b'<script data-key="' + b'a' * 26 + b'" type="application/json" data-mo1-public-services '
         b'data-api="https://the-museum-of-one.ghost.io/ghost/api/content/">{}</script>'
     )
    q=parse_qs(urlsplit(url).query)
    assert q['key'] == ['a' * 26]
    page=int(q['page'][0]);kind='posts' if '/posts/' in url else 'pages';rid=('%024x'%page) if kind=='posts' else ('%024x'%(page+10))
    return encoded({kind:[{'id':rid}], 'meta':{'pagination':{'next':2 if page==1 else None}}})
  policy={'max_records':10,'content_api_origin':'https://the-museum-of-one.ghost.io'};self.assertEqual(len(fetch_collection(API(),policy)),4)
 def test_public_services_config_requires_exact_key_and_target(self):
  origin='https://the-museum-of-one.ghost.io'
  def marker(key, target=origin):
   return (f'<script type="application/json" data-mo1-public-services data-key="{key}" '
           f'data-api="{target}/ghost/api/content/">{{}}</script>')
  for html in ('<script>var demo={contentKey:"example-placeholder"}</script>',
               marker('a' * 25), marker('a' * 26 + 'z'), marker('a' * 26, origin + '.example')):
   config=PublicContentAPI(origin)
   config.feed(html)
   with self.assertRaisesRegex(FetchFailure,'configuration unavailable'):
    config.key()
  config=PublicContentAPI(origin)
  config.feed(marker('a' * 26) + marker('b' * 26))
  with self.assertRaisesRegex(FetchFailure,'configuration is ambiguous'):
   config.key()
 def test_only_an_exact_legacy_alternate_can_supply_a_fallback_key(self):
  config=PublicContentAPI('https://the-museum-of-one.ghost.io')
  config.feed('<link rel="alternate" type="application/json" '
              'href="https://[invalid/ghost/api/content/pages/?key=' + 'c' * 26 + '">'
              '<link rel="alternate" type="application/json" '
              'href="https://example.org/ghost/api/content/pages/?key=' + 'b' * 26 + '">'
              '<link rel="alternate" type="application/json" '
              'href="/ghost/api/content/pages/?key=' + 'a' * 26 + '&amp;filter=visibility%3Apublic">')
  self.assertEqual(config.key(),'a' * 26)
 def test_source_failure_clears_readable_output_without_losing_checkpoint(self):
  from website_sync import main
  from unittest.mock import patch
  s,p,_=self.run_sync();before=(self.work/'state.json').read_bytes()
  (self.root/'data/source').mkdir(parents=True);(self.root/'data/source/ghost-discovery.json').write_text('{"records":[]}')
  (self.root/'config/website-sync.json').write_text(json.dumps(self.policy))
  with patch('website_sync.ROOT',self.root),patch('website_sync.fetch_collection',side_effect=FetchFailure('no source')),patch('sys.argv',['sync','--work',str(self.work)]):main()
  self.assertEqual(json.loads((self.work/'public/current.json').read_text()),[])
  self.assertEqual(json.loads((self.work/'public/discovery.json').read_text())['records'],[])
  self.assertEqual((self.work/'state.json').read_bytes(),before)
 def test_retry_backoff_is_bounded_and_errors_do_not_log_request_keys(self):
  from website_sync import Fetcher
  from urllib.error import URLError
  sleeps=[];f=Fetcher(sleep=sleeps.append)
  with patch.object(f.opener,'open',side_effect=URLError('sensitive request key')):
   with self.assertRaises(FetchFailure) as ctx:f.get('https://www.museumofone.art/')
  self.assertEqual(sleeps,[1,2,4]);self.assertNotIn('key',str(ctx.exception))
 def test_feature_caption_label_is_plain_text_while_credit_and_source_are_retained(self):
  caption='<a href="https://example.org/credit">Yongjae Kim, <i>Classon Ave</i></a> &amp; archive'
  self.row['record'].update(feature_image='https://www.museumofone.art/content/images/fixture.png',feature_image_alt=None,feature_image_caption=caption)
  state,rows,_=self.run_sync();image=next(a for a in rows[0]['attachments'] if a['role']=='image')
  self.assertEqual(image['label'],'Yongjae Kim, Classon Ave & archive')
  self.assertEqual(rows[0]['source']['feature_image_caption'],caption)
  self.assertEqual(rows[0]['source']['html'],self.row['record']['html'])
  out=self.root/'dist';out.mkdir()
  def write(path,text):
   file=out/path;file.parent.mkdir(parents=True,exist_ok=True);file.write_text(text)
  build_website_pages(self.work,out,write,lambda title,description,content,*args,**kwargs:content,'https://archive.museumofone.art')
  rendered=(out/'website'/('web-'+RID+'.html')).read_text()
  self.assertIn('alt="Yongjae Kim, Classon Ave &amp; archive"',rendered)
  self.assertNotIn('alt="&lt;a',rendered)
  state,rows,report=self.run_sync(state=state)
  self.assertEqual(report['changes'][0]['action'],'unchanged')
  self.assertEqual(len(state['records'][RID]['revisions']),1)
 def test_explicit_feature_alt_is_preferred_to_caption(self):
  self.row['record'].update(feature_image='https://www.museumofone.art/content/images/fixture.png',feature_image_alt='Checked image description',feature_image_caption='<em>Credit only</em>')
  _,rows,_=self.run_sync()
  self.assertEqual(next(a for a in rows[0]['attachments'] if a['role']=='image')['label'],'Checked image description')
 def test_remote_image_only_link_keeps_destination_label_and_inert_source(self):
  doi='https://doi.org/10.5281/zenodo.17111649';image='https://img.shields.io/badge/DOI-record-blue.svg'
  html=f'<p><a href="{doi}"><span><img src="{image}" alt="DOI &lt;checked&gt; &amp; citation"></span></a></p>'
  self.row['record']['html']=html
  state,rows,_=self.run_sync();body=rows[0]['readable_html']
  self.assertIn(f'<a href="{doi}" rel="noopener noreferrer"><span></span>DOI &lt;checked&gt; &amp; citation</a>',body)
  self.assertEqual(body.count('<a '),1);self.assertNotIn('<img',body);self.assertNotIn('<checked>',body)
  self.assertEqual(rows[0]['source']['html'],html)
  attachment=next(a for a in rows[0]['attachments'] if a['url']==image)
  self.assertEqual(attachment['storage'],'external_link_only')
  out=self.root/'dist';out.mkdir()
  def write(path,text):
   file=out/path;file.parent.mkdir(parents=True,exist_ok=True);file.write_text(text)
  build_website_pages(self.work,out,write,lambda title,description,content,*args,**kwargs:content,'https://archive.museumofone.art')
  rendered=(out/'website'/('web-'+RID+'.html')).read_text()
  self.assertIn(f'href="{doi}"',rendered);self.assertIn(f'href="{image}"',rendered)
  self.assertNotIn(f'<img src="{image}"',rendered)
  self.assertIn('DOI <checked> & citation',rows[0]['text'])
  state2,rows2,report=self.run_sync(state=state)
  self.assertEqual(rows2[0]['readable_html'],body);self.assertEqual(report['changes'][0]['action'],'unchanged')
  self.assertEqual(state2['records'][RID]['revisions'],state['records'][RID]['revisions'])
 def test_link_image_fallback_does_not_duplicate_visible_text_or_remove_source_reference(self):
  image='https://external.example/badge.svg'
  body=''.join(Readable(f'<a href="/read/"><img src="{image}" alt="Read now"><strong>Read now</strong></a>').parts)
  self.assertEqual(body.count('Read now'),1);self.assertEqual(body.count('<a '),1)
  body=''.join(Readable(f'<a href="/read/" aria-label="Read the deposited edition"><img src="{image}" alt=""></a>').parts)
  self.assertIn('>Read the deposited edition</a>',body)
  parser=Readable(f'<img src="{image}" alt="Standalone illustration">')
  self.assertIn('Standalone illustration — image at source</a>',''.join(parser.parts))
  self.assertEqual(parser.links,[{'url':image,'role':'image','label':'Standalone illustration'}])
 def test_weganda_capture_preserves_native_reader_with_only_verified_inline_images(self):
  source='https://www.museumofone.art/external-records/'
  origin='https://archive.museumofone.art'
  image='https://www.museumofone.art/content/images/page.webp'
  path='assets/website-captures/'+'a'*64+'.webp'
  markup=(f'<details class="moo-weganda-reader" open><summary>Read the archived copy</summary>'
          '<nav><a href="#page-1">Page 1</a></nav><div class="moo-weganda-viewport">'
          f'<figure id="page-1"><img src="{image}" alt="Page 1 &amp; cover"></figure>'
          '<figure><img src="https://example.com/remote.webp" alt="Other page"></figure></div>'
          '<style>body {display:none}</style></details><details><summary>Other disclosure</summary></details>')
  sanitized=''.join(Readable(markup,source).parts)
  self.assertEqual(sanitized.count('<details class="capture-pdf-reader">'),1)
  self.assertIn('<summary>Read the archived copy</summary>',sanitized)
  self.assertIn(f'href="{source}#page-1"',sanitized)
  self.assertNotIn('<style',sanitized)
  self.assertIn('</details>Other disclosure',sanitized)
  outside=''.join(Readable(markup,'https://www.museumofone.art/another-page/').parts)
  self.assertNotIn('capture-pdf-reader',outside)
  asset={'url':image,'storage':'local_archival_file','mime_type':'image/webp','archive_path':path,
         'pixel_dimensions':{'width':1275,'height':1650}}
  rendered,embedded=inline_pdf_reader_pages(sanitized,[asset],origin)
  self.assertEqual(embedded,{path})
  self.assertIn(f'src="{origin}/{path}" width="1275" height="1650" alt="Page 1 &amp; cover"',rendered)
  self.assertIn('href="https://example.com/remote.webp"',rendered)
  self.assertEqual(rendered.count('<img '),1)
  self.assertEqual(inline_pdf_reader_pages(sanitized,[],origin),(sanitized,set()))
 def test_dialogue_captures_preserve_only_their_native_pdf_readers(self):
  for slug,prefix in (('tomoki-akimaru','akimaru'),('lu-peng','lu-peng')):
   with self.subTest(slug=slug):
    page=f'https://www.museumofone.art/{slug}/'
    jump=f'{prefix}-copy-01-page-1'
    raw=(f'<details class="moo-{prefix}-reader" open><summary>Archived copy</summary>'
         f'<nav aria-label="PDF pages"><a href="#{jump}">Page 1</a>'
         '<a href="/content/files/edition.pdf">Open PDF</a></nav>'
         f'<div class="moo-{prefix}-viewport" aria-label="PDF edition">'
         f'<figure id="{jump}"><img src="/content/images/page.webp" alt="Page 1"></figure>'
         '</div><script>untrusted()</script></details>')
    reader=Readable(raw,page)
    rendered=''.join(reader.parts)
    self.assertIn('<details class="capture-pdf-reader"><summary>Archived copy</summary>',rendered)
    self.assertIn('role="region" tabindex="0" aria-label="PDF edition"',rendered)
    self.assertIn(f'href="{page}#{jump}"',rendered)
    self.assertIn(f'id="{jump}"',rendered)
    self.assertNotIn('<script',rendered)
    self.assertNotIn('open>',rendered)
    other=Readable(raw,'https://www.museumofone.art/another/')
    self.assertNotIn('capture-pdf-reader',''.join(other.parts))
    self.assertEqual(reader.links[1:],other.links[1:])

 def test_media_sources_and_site_images_are_detected(self):
  parser=Readable('<video><source src="/content/media/a.mp4"></video><audio src="/content/media/b.mp3"></audio><img src="/content/images/c.png">')
  self.assertEqual({x['role'] for x in parser.links},{'source','audio','image'})
  self.assertIn('https://www.museumofone.art/content/media/a.mp4',{x['url'] for x in parser.links})
 def test_only_research_record_toggle_heading_gets_h2_fallback(self):
  raw=('<h4 class="kg-toggle-heading-text">Research record and citation</h4>'
       '<h4 class="kg-toggle-heading-text"><span style="white-space: pre-wrap;">Research record and citation</span></h4>'
       '<h4 class="kg-toggle-heading-text">Different citation title</h4>'
       '<h4>Research record and citation</h4>')
  rendered=''.join(Readable(raw).parts)
  self.assertIn('<h2>Research record and citation</h2>',rendered)
  self.assertIn('<h2><span>Research record and citation</span></h2>',rendered)
  self.assertIn('<h4>Different citation title</h4>',rendered)
  self.assertIn('<h4>Research record and citation</h4>',rendered)
  self.assertNotIn('style=',rendered)
 def test_korean_runs_are_labelled_without_replacing_existing_language(self):
  raw=('<p>English title (임동식 and 김구림) with notes.</p>'
       '<div lang="ko-KR"><p><em>한국어</em></p></div><p>Later 문장.</p>'
       '<script>나쁜 스크립트</script>')
  for slug in ('dong-yeon-koh','when-documentation-becomes-the-work'):
   with self.subTest(slug=slug):
    parser=Readable(raw,'https://www.museumofone.art/'+slug+'/')
    rendered=''.join(parser.parts)
    self.assertIn('English title (<span lang="ko">임동식</span> and <span lang="ko">김구림</span>) with notes.',rendered)
    self.assertIn('<div lang="ko-KR"><p><em>한국어</em></p></div>',rendered)
    self.assertIn('Later <span lang="ko">문장</span>.',rendered)
    self.assertNotIn('나쁜 스크립트',rendered)
    self.assertNotIn('lang=', ''.join(parser.text))
  self.assertNotIn('<span lang=', ''.join(Readable(raw,'https://www.museumofone.art/other/').parts))
 def test_koh_reader_keeps_safe_page_navigation_and_captured_pdf(self):
  source='https://www.museumofone.art/dong-yeon-koh/'
  image='https://www.museumofone.art/content/images/koh-page.webp'
  pdf='https://www.museumofone.art/content/files/koh-paper.pdf'
  path='assets/website-captures/'+'b'*64+'.webp'
  markup=(f'<details class="moo-koh-reader" open onclick="alert(1)"><summary>Read the archived copy</summary>'
          '<nav class="moo-koh-reader-nav" aria-label="Pages for A &amp; B">'
          f'<a href="#koh-copy-21-page-1">Page 1</a><a href="{pdf}">Open PDF</a></nav>'
          '<div class="moo-koh-viewport" aria-label="Scrollable pages for A &amp; B">'
          f'<figure id="koh-copy-21-page-1"><img src="{image}" alt="Page 1" onerror="alert(1)"></figure>'
          '<script>bad script</script></div></details>')
  reader=Readable(markup,source)
  sanitized=''.join(reader.parts)
  self.assertIn('<details class="capture-pdf-reader">',sanitized)
  self.assertIn('aria-label="Pages for A &amp; B"',sanitized)
  self.assertIn('tabindex="0" aria-label="Scrollable pages for A &amp; B"',sanitized)
  self.assertIn(f'href="{source}#koh-copy-21-page-1"',sanitized)
  self.assertIn('id="koh-copy-21-page-1"',sanitized)
  self.assertIn(pdf,{link['url'] for link in reader.links})
  self.assertNotRegex(sanitized,r'onclick|onerror|<script|bad script|<details[^>]+ open')
  self.assertNotIn('capture-pdf-reader',''.join(Readable(markup,'https://www.museumofone.art/another-page/').parts))
  asset={'url':image,'storage':'local_archival_file','mime_type':'image/webp','archive_path':path,
         'pixel_dimensions':{'width':1275,'height':1650}}
  rendered,embedded=inline_pdf_reader_pages(sanitized,[asset],'https://archive.example')
  self.assertEqual(embedded,{path})
  self.assertIn(f'src="https://archive.example/{path}" width="1275" height="1650" alt="Page 1"',rendered)
  self.assertIn(f'href="{pdf}"',rendered)
 def test_first_party_pdf_objects_are_preserved_without_embedded_fallback(self):
  pdf='https://www.museumofone.art/content/files/object.PDF'
  self.row['record']['html']=(
   f'<object type="application/pdf" data="{pdf}">'
   '<iframe src="/content/files/object-fallback.pdf"></iframe>'
   '<embed src="/content/files/embedded-fallback.pdf">'
   '<object data="/content/files/nested.pdf"></object>'
   '</object>'
   '<iframe src="/preview/"><object data="/content/files/frame-fallback.pdf"></object></iframe>'
   '<object type="application/pdf" data="https://another.example/document.pdf"></object>'
   '<object data="/content/files/different-format.svg"></object>'
   f'<a href="{pdf}"><object data="{pdf}"></object></a>'
   '<p>Still readable.</p>'
  )
  data=b'%PDF-1.7 fixture'
  _,captures,report=self.run_sync(fetcher=Fetch(data))
  capture,=captures
  attachment,=capture['attachments']
  self.assertEqual((attachment['url'],attachment['role'],attachment['sha256']),(pdf,'object',digest(data)))
  self.assertEqual(attachment['mime_type'],'application/pdf')
  self.assertEqual((self.work/'public'/attachment['archive_path']).read_bytes(),data)
  self.assertEqual(report['failed_attachments'],0)
  body=capture['readable_html']
  self.assertIn(f'<p><a href="{pdf}">Source PDF</a></p>',body)
  self.assertIn(f'<a href="{pdf}" rel="noopener noreferrer">Source PDF</a>',body)
  self.assertIn('<p>Still readable.</p>',body)
  self.assertNotRegex(body,r'<(?:object|iframe|embed)\b|fallback\.pdf|nested\.pdf|another\.example|different-format')
 def test_ghost_fallback_never_keeps_frozen_website_text(self):
  from website_cache import fallback
  data={'schema_version':2,'index_kind':'discovery','canonical_origin':'https://archive.museumofone.art','counts':{'publication':1,'website':1},'records':[{'id':'publication:1','kind':'publication','relationships':[{'target_id':'website:x'}]},{'id':'website:x','kind':'website','title':'Previously public source','relationships':[]}],'content_version':'a'*64}
  p=fallback(data);self.assertEqual(len(p['records']),1);self.assertFalse(p['records'][0]['relationships']);self.assertNotIn('Previously public source',encoded(p).decode());self.assertEqual(data['records'][1]['title'],'Previously public source')
 def test_asset_cache_reuses_ciphertext_with_valid_source_etag(self):
  import base64,os
  from unittest.mock import MagicMock
  from website_sync import open_cached_asset
  secret=base64.urlsafe_b64encode(b'x'*32).decode().rstrip('=')
  self.row['record']['html']='<a href="/content/files/a.pdf">PDF</a>'
  url='https://www.museumofone.art/content/files/a.pdf';first=Fetch(b'%PDF-cache-fixture');first.response_headers={url:{'ETag':'v1'}}
  with patch.dict(os.environ,{'MOO_ASSET_CACHE_KEY':secret}):
   s,p,_=self.run_sync(fetcher=first);a=p[0]['attachments'][0];vault=self.work/'vault/assets'/(a['sha256']+'.json')
   self.assertEqual(open_cached_asset(vault,b'x'*32),b'%PDF-cache-fixture')
   self.assertEqual(unseal(vault.read_bytes(),self.private,None)['sha256'],a['sha256'])
   second=Fetch(FetchFailure('A body download must not be needed'));second.opener=MagicMock();second.opener.open.return_value.__enter__.return_value.headers={'ETag':'v1'};second.reused_assets=0
   s2,p2,r=self.run_sync(state=s,fetcher=second);self.assertEqual(r['reused_asset_downloads'],1);self.assertEqual(p2[0]['attachments'][0]['sha256'],a['sha256']);self.assertNotIn(secret,encoded(s2).decode())
 def test_unknown_uploaded_type_preserved_inertly_and_budget_is_explicit(self):
  self.row['record']['html']='<a href="/content/files/data.hdf5">Data</a>'
  s,p,r=self.run_sync(fetcher=Fetch(b'original binary'));self.assertTrue(p[0]['attachments'][0]['archive_path'].endswith('.bin'));self.assertEqual(p[0]['attachments'][0]['bytes'],15)
  self.policy['max_total_asset_bytes']=1;s,p,r=self.run_sync(fetcher=Fetch(b'original binary'));self.assertEqual(p[0]['attachments'][0]['availability'],'deferred');self.assertNotIn('archive_path',p[0]['attachments'][0])
 def test_host_mime_database_cannot_create_duplicate_revisions(self):
  self.row['record']['html']='<img src="/content/images/favicon.ico">'
  with patch('mimetypes.guess_type',return_value=('image/x-icon',None)):s,p,r=self.run_sync(fetcher=Fetch(b'icon bytes'))
  with patch('mimetypes.guess_type',return_value=('application/octet-stream',None)):s2,p2,r2=self.run_sync(state=s,fetcher=Fetch(b'icon bytes'))
  self.assertEqual(p[0]['attachments'][0]['mime_type'],'image/vnd.microsoft.icon');self.assertEqual(s['records'][RID]['revisions'],s2['records'][RID]['revisions'])
if __name__=='__main__':unittest.main()
