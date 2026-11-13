import copy,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from website_sync import reconcile,projection,Readable,FetchFailure,seal,unseal,fetch_collection,digest,encoded
from website_pages import build_website_pages,access_asset
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
    if url.endswith('.art/'):return b'contentKey:"abcdef0123456789"'
    q=parse_qs(urlsplit(url).query);page=int(q['page'][0]);kind='posts' if '/posts/' in url else 'pages';rid=('%024x'%page) if kind=='posts' else ('%024x'%(page+10))
    return encoded({kind:[{'id':rid}], 'meta':{'pagination':{'next':2 if page==1 else None}}})
  policy={'max_records':10,'content_api_origin':'https://the-museum-of-one.ghost.io'};self.assertEqual(len(fetch_collection(API(),policy)),4)
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
 def test_media_sources_and_site_images_are_detected(self):
  parser=Readable('<video><source src="/content/media/a.mp4"></video><audio src="/content/media/b.mp3"></audio><img src="/content/images/c.png">')
  self.assertEqual({x['role'] for x in parser.links},{'source','audio','image'})
  self.assertIn('https://www.museumofone.art/content/media/a.mp4',{x['url'] for x in parser.links})
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
