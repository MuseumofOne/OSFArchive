import json,sys,unittest
from pathlib import Path
from html.parser import HTMLParser
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from explorer import render_explorer
from integration_search import searchable_text

class Inspect(HTMLParser):
 def __init__(self,text):
  super().__init__();self.ids=[];self.tags=[];self.links=[];self.feed(text)
 def handle_starttag(self,tag,attrs):
  a=dict(attrs);self.tags.append(tag)
  if a.get('id'):self.ids.append(a['id'])
  if a.get('href'):self.links.append(a['href'])

class ExplorerContract(unittest.TestCase):
 def fixture(self):
  return [{'id':'123','title':'A title <script> & {{unsafe}}','short_title':'An edition','author':'Writer','date':'2026','collection':'Books & volumes','type':'Book','summary':'Editorial description','subjects':['Witnessing'],'accession':'MOO-CAT-001','contents':[],'entity_links':[]}]
 def test_shared_renderer_preserves_fallback_and_host_heading_identity(self):
  archive=render_explorer(self.fixture(),[],'https://archive.museumofone.art',standalone=True)
  ghost=render_explorer(self.fixture(),[],'https://archive.museumofone.art')
  a,g=Inspect(archive),Inspect(ghost)
  self.assertEqual(a.ids,g.ids);self.assertEqual(len(a.ids),len(set(a.ids)))
  self.assertEqual(a.tags.count('h1'),1);self.assertEqual(g.tags.count('h1'),0)
  self.assertNotIn('iframe',g.tags)
  self.assertIn('items/123.html',a.links)
  self.assertIn('https://archive.museumofone.art/items/123.html',g.links)
  self.assertNotIn('{{unsafe}}',ghost);self.assertNotIn('<script> &',ghost)
 def test_catalogue_filter_uses_shared_identifier_and_context_scope(self):
  record=self.fixture()[0]
  record.update(isbn='978-1-06-982034-1',keywords=['Source keyword'],alternate_titles=[{'title':'Source title variant'}],entity_links=[{'id':'artist','label':'A discussed artist'}])
  html=render_explorer([record],[],'https://archive.museumofone.art')
  class SearchAttributes(HTMLParser):
   def __init__(self,text):
    super().__init__();self.search=[];self.feed(text)
   def handle_starttag(self,tag,attrs):
    a=dict(attrs)
    if tag=='article' and 'data-ax-record' in a:self.search.append(a['data-search'])
  searches=SearchAttributes(html).search
  self.assertTrue(searches)
  self.assertTrue(all(value==searchable_text(record) for value in searches))
  for term in ['978-1-06-982034-1','Source keyword','Source title variant','A discussed artist']:
   self.assertTrue(all(term in value for value in searches))
 def test_generated_partial_and_current_homepage_have_same_catalogue(self):
  fragment=(ROOT/'dist/integration/archive-explorer.hbs').read_text()
  page=(ROOT/'dist/index.html').read_text()
  self.assertEqual(page.count('data-archive-explorer'),1)
  self.assertEqual(fragment.count('data-ax-record='),20)
  # Four featured descriptions plus every one of the sixteen catalogue records.
  for row in json.loads((ROOT/'data/catalogue.json').read_text()):
   self.assertIn('data-ax-record="'+row['id']+'"',fragment)
   self.assertIn('data-ax-record="'+row['id']+'"',page)

if __name__=='__main__':unittest.main()
