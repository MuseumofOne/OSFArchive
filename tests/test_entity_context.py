"""Preserve role boundaries in subject metadata and web-only contextual records."""
import json
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from entities import entity_graph
from metadata import build_graph
from identities import work_uri

class EntityContext(unittest.TestCase):
    def test_correspondence_is_not_subject_or_authorship(self):
        entities=json.loads((ROOT/'data/entities.json').read_text())
        markov=next(x for x in entities if x['id']=='alexander-viktorovich-markov')
        graph=entity_graph(entities,'https://archive.example')['@graph']
        node=next(x for x in graph if x['name']==markov['label'])
        self.assertFalse(node['subjectOf'])
        from test_research_discovery import inputs
        records, _, _, _ = inputs()
        r = next(r for r in records if any(e['id'] == markov['id'] for e in r['entity_links']))
        work=next(x for x in build_graph(r,'https://archive.example/items/test.html','https://archive.example')['@graph'] if x['@id']==work_uri(r,'https://archive.example'))
        self.assertIn('mentions',work)
        self.assertNotIn({'@id': node['@id']}, work.get('about', []))
        self.assertNotIn(markov['label'], str(work.get('author', {})))

    def test_web_context_does_not_create_an_affiliation(self):
        entities=json.loads((ROOT/'data/entities.json').read_text())
        graph=entity_graph(entities,'https://archive.example')['@graph']
        for name in ['Dong-Yeon Koh','Paul Gladston']:
            node=next(x for x in graph if x['name']==name)
            self.assertEqual(node['subjectOf'][0]['@type'],'WebPage')
            for field in ['affiliation','memberOf','worksFor','author','contributor']:
                self.assertNotIn(field,node)
            self.assertNotIn('ProfilePage',str(node))

    def test_name_variant_is_preserved(self):
        entities=json.loads((ROOT/'data/entities.json').read_text())
        self.assertIn('Kazuo Shiraga',next(x for x in entities if x['id']=='shiraga-kazuo')['variants'])

    def test_description_snippet_ends_at_word_boundary(self):
        import ast
        module=ast.parse((ROOT/'scripts/build.py').read_text())
        function=next(n for n in module.body if isinstance(n,ast.FunctionDef) and n.name=='description_excerpt')
        scope={}
        exec(compile(ast.Module(body=[function],type_ignores=[]),'snippet','exec'),scope)
        text='Short complete words ending here'
        result=scope['description_excerpt'](text,20)
        self.assertLessEqual(len(result),20)
        self.assertEqual(result,'Short complete…')
