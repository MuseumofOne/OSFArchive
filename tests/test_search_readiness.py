"""Crawler-facing contracts across the generated catalogue, not ranking claims."""
import hashlib
import json
from html.parser import HTMLParser
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / 'dist'

class Head(HTMLParser):
    def __init__(self, text):
        super().__init__(); self.meta = {}; self.canonical = []; self.feed(text)
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == 'meta': self.meta[a.get('name') or a.get('property')] = a.get('content')
        if tag == 'link' and a.get('rel') == 'canonical': self.canonical.append(a['href'])

class SearchReadiness(unittest.TestCase):
    def test_home_uses_root_and_sitemap_agrees(self):
        h = Head((DIST/'index.html').read_text())
        self.assertEqual(h.canonical, ['https://archive.museumofone.art/'])
        ns = {'s':'http://www.sitemaps.org/schemas/sitemap/0.9'}
        loc = [e.text for e in ET.parse(DIST/'sitemap.xml').findall('s:url/s:loc', ns)]
        self.assertIn(h.canonical[0], loc)
        self.assertNotIn(h.canonical[0]+'index.html', loc)
        self.assertNotIn('https://archive.museumofone.art/404.html', loc)

    def test_scholar_pdfs_are_byte_identical_siblings(self):
        for path in (DIST/'items').glob('*.html'):
            h = Head(path.read_text())
            pdf = h.meta.get('citation_pdf_url')
            if not pdf: continue
            self.assertEqual(pdf, 'https://archive.museumofone.art/items/'+path.stem+'.pdf')
            self.assertEqual(hashlib.sha256(path.with_suffix('.pdf').read_bytes()).digest(),
                             hashlib.sha256((DIST/'assets/documents'/f'{path.stem}.pdf').read_bytes()).digest())

    def test_datasets_expose_real_description_and_download(self):
        for rid in ('20100136','20100139'):
            graph = json.loads((DIST/'metadata'/f'{rid}.jsonld').read_text())['@graph']
            nodes = {x['@id']:x for x in graph}
            dataset = next(x for x in graph if x.get('@type') == 'Dataset')
            self.assertTrue(50 <= len(dataset['description']) <= 5000)
            self.assertTrue(dataset['distribution'])
            for ref in dataset['distribution']:
                download = nodes[ref['@id']]
                self.assertEqual(download['@type'], 'DataDownload')
                self.assertEqual(download['encodingFormat'], 'application/pdf')
                self.assertTrue(download['contentUrl'].startswith(('https://zenodo.org/', 'https://archive.museumofone.art/assets/documents/')))
            page = (DIST/'items'/f'{rid}.html').read_text()
            self.assertIn('repository-description-text', page)
            self.assertNotIn('<summary>Read the complete repository description', page)

if __name__ == '__main__': unittest.main()
