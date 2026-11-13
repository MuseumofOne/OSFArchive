"""Persistent navigation must advertise the same collection as its destination."""
from collections import Counter
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import check
from institutional import collection_tree
from publication_arrangement import publication_inventory


class SidebarCounts(unittest.TestCase):
    def setUp(self):
        self.records = [
            {'id': '1', 'title': 'Book', 'accession': 'MOO-1', 'collection': 'Books & volumes'},
            {'id': '2', 'title': 'Method', 'accession': 'MOO-2', 'collection': 'Methodology'},
        ]
        self.full = {'Books & volumes': 2, 'Methodology': 3}
        self.cards = Counter({('Books & volumes', 'edition'): 1, ('Books & volumes', 'website'): 1,
                              ('Methodology', 'edition'): 1, ('Methodology', 'website'): 2})

    def evaluate(self, markup, name='methodology.html'):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(markup)
            page = check.Page(path)
            with patch.object(check, 'DIST', root), patch.object(check, 'ERRORS', []):
                check.check_collection_trees({path: page}, self.full, self.cards)
                return list(check.ERRORS), page

    def render(self, path='methodology.html'):
        return collection_tree(path, self.records, [], collection_counts=self.full)

    def test_full_scope_and_format_breakdown_match_each_destination(self):
        errors, page = self.evaluate(self.render())
        self.assertEqual(errors, [])
        self.assertEqual(page.tree_counts['data-tree-total', ''], ['5 catalogue records'])
        self.assertEqual(page.tree_counts['data-tree-breakdown', 'Methodology'],
                         ['1 deposited edition · 2 website records'])
        markup = self.render()
        self.assertLess(markup.index('data-tree-collection="Methodology"'), markup.index('href="items/2.html"'))
        self.assertIn('class="tree-list-label">Deposited editions</p>', markup)

    def test_nested_item_pages_use_the_same_counts_with_relative_destinations(self):
        errors, page = self.evaluate(self.render('items/1.html'), 'items/1.html')
        self.assertEqual(errors, [])
        self.assertEqual(page.tree_links['Methodology', '../methodology.html'], 1)

    def test_old_deposit_only_count_is_rejected_even_when_all_items_exist(self):
        errors, _ = self.evaluate(self.render().replace('3 catalogue records</strong>', '1 deposited edition</strong>'))
        self.assertTrue(any('count or breakdown' in error for error in errors))

    def test_wrong_destination_is_rejected_with_correct_totals(self):
        markup = self.render().replace('href="methodology.html"', 'href="catalogue.html"')
        errors, _ = self.evaluate(markup)
        self.assertTrue(any('links differ' in error for error in errors))

    def test_duplicate_or_missing_sidebar_is_rejected(self):
        for markup in ('<main>No navigation</main>', self.render() * 2):
            errors, _ = self.evaluate(markup)
            self.assertTrue(any('Missing or duplicate' in error for error in errors))

    def test_ghost_publication_reclassification_and_withdrawal_refresh_sidebar(self):
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        from website_sync import reconcile

        class NoAssets:
            def document_language(self, url):
                return 'en'

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'config').mkdir()
            key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
            (root / 'config/key.pem').write_bytes(key.public_key().public_bytes(
                serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo))
            policy = {'public_key': 'config/key.pem', 'max_attachment_bytes': 100000,
                      'max_total_asset_bytes': 200000}
            row = {'kind': 'post', 'record': {
                'id': 'a' * 24, 'title': 'New methodology paper',
                'url': 'https://www.museumofone.art/new-methodology-paper/',
                'visibility': 'public', 'status': 'published',
                'published_at': '2026-11-01T00:00:00Z', 'updated_at': '2026-11-01T00:00:00Z',
                'html': '<p>A newly published research method.</p>',
                'authors': [{'name': 'Dorian Vale'}],
                'tags': [{'name': 'Methodology', 'visibility': 'public'}],
            }}
            state = None
            stable_id = None
            for target, expected_group in (('Methodology', 'Methodology'),
                                            ('Theory & treatises', 'Theory & treatises'),
                                            (None, None)):
                with self.subTest(target=target):
                    row['record']['tags'] = [{'name': target, 'visibility': 'public'}] if target else []
                    state, captures, _ = reconcile([row] if target else [], state, root, root / 'work', policy,
                                                    NoAssets(), at='2026-11-13T00:00:00Z')
                    arranged = publication_inventory(captures, self.records)
                    self.assertEqual([record['collection'] for record in arranged],
                                     [expected_group] if target else [])
                    if captures:
                        if stable_id is None:
                            stable_id = captures[0]['archive_id']
                        self.assertEqual(captures[0]['archive_id'], stable_id)
                    website = [record for record in arranged if record['collection'] and not record['edition_path']]
                    self.full = Counter(record['collection'] for record in self.records + website)
                    self.cards = Counter((record['collection'], 'edition') for record in self.records)
                    self.cards.update((record['collection'], 'website') for record in website)
                    for path in ('methodology.html', 'items/1.html'):
                        errors, page = self.evaluate(self.render(path), path)
                        self.assertEqual(errors, [])
                        self.assertEqual(page.tree_counts['data-tree-total', ''],
                                         ['3 catalogue records' if target else '2 catalogue records'])
                        method_count = 2 if target == 'Methodology' else 1
                        self.assertEqual(page.tree_counts['data-tree-full-count', 'Methodology'],
                                         [f'{method_count} catalogue ' + ('record' if method_count == 1 else 'records')])
                        if target == 'Theory & treatises':
                            self.assertEqual(page.tree_counts['data-tree-breakdown', target],
                                             ['0 deposited editions · 1 website record'])
                    if not target:
                        self.assertEqual(state['records']['a' * 24]['access_status'], 'withheld')


if __name__ == '__main__':
    unittest.main()
