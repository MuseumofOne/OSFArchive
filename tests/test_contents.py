"""Analytic records must identify their parent and reproduce checked PDF evidence."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from contents import attach_contents, build_content_pages, component_schema


class AnalyticContents(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads((ROOT / "data/contents.json").read_text())
        cls.records = json.loads((ROOT / "data/catalogue.json").read_text())

    def attached(self):
        return attach_contents(deepcopy(self.records), self.data)

    def test_complete_component_counts_and_idempotent_attachment(self):
        attached = self.attached()
        expected = {"19864099": 14, "19864115": 12, "23395654": 17, "20383926": 14}
        self.assertEqual({r["id"]: len(r["contents"]) for r in attached if r["contents"]}, expected)
        self.assertEqual(attached, attach_contents(deepcopy(attached), self.data))
        self.assertNotIn("reference", self.data["books"]["19864099"]["components"][0])
        for record in attached:
            for index, part in enumerate(record["contents"], 1):
                self.assertEqual(part["reference"], f'{record["accession"]}/C{index:03}')
                self.assertEqual(part["parent_doi"], record["doi"])
                self.assertNotIn("doi", part)
                self.assertIn("inherited", part["creator_inheritance"])

    def test_titles_and_pagination_against_actual_source_pdfs(self):
        try:
            import fitz
        except ImportError:
            self.skipTest("PyMuPDF is only required for source-PDF verification")
        for rid, book in self.data["books"].items():
            path = ROOT / "dist" / book["source"]["file"]
            if not path.exists():
                self.skipTest("Source reading-copy PDFs are not present")
            with fitz.open(path) as document:
                self.assertEqual(len(document), book["source"]["page_count"])
                last_end = 0
                for part in book["components"]:
                    with self.subTest(book=rid, component=part["id"]):
                        start, end = part["pdf_start"], part["pdf_end"]
                        self.assertLess(last_end, start)
                        self.assertLessEqual(start, end)
                        self.assertLessEqual(end, len(document))
                        page = document[start - 1]
                        blocks = page.get_text("blocks")
                        heading = blocks[1][4] if part.get("number") else blocks[0][4]
                        heading = " ".join(heading.split()).replace("\xad", "-")
                        self.assertEqual(part["title"], heading)
                        self.assertEqual(page.get_text().splitlines()[-1], part["printed_start"])
                        self.assertEqual(document[end - 1].get_text().splitlines()[-1], part["printed_end"])
                        self.assertEqual(part["evidence"]["pdf_pages"], [start, end])
                        last_end = end

    def test_part_identity_is_separate_from_edition_doi(self):
        record = self.attached()[0]
        part = record["contents"][1]
        graph = component_schema(record, part, "https://archive.example/")["@graph"]
        child = next(node for node in graph if node["@id"].endswith("#component"))
        parent = next(node for node in graph if node["@type"] == "Book")
        self.assertEqual(parent["@id"], "https://doi.org/" + record["doi"])
        self.assertEqual(child["isPartOf"], {"@id": parent["@id"]})
        self.assertEqual(parent["hasPart"], {"@id": child["@id"]})
        self.assertEqual(child["identifier"]["value"], part["reference"])
        self.assertNotEqual(child["@id"], parent["@id"])
        self.assertEqual(child["pageStart"], "1")
        self.assertIn("#page=9", child["encoding"]["contentUrl"])

    def test_pages_include_reversible_navigation_and_source_context(self):
        output = {}
        schemas = {}
        def layout(title, description, content, path="index.html", base="", active="", schema=None):
            schemas[path] = schema
            return content
        paths = build_content_pages(deepcopy(self.records), self.data, output.__setitem__, layout, "https://archive.example")
        self.assertEqual(len(paths), 58)
        self.assertEqual(len(set(paths)), 58)
        self.assertIn("contents.html", paths)
        record = self.attached()[0]
        for part in record["contents"]:
            html = output[part["url"]]
            self.assertIn(f'../read/{record["id"]}.html#page={part["pdf_start"]}', html)
            self.assertIn(f'../items/{record["id"]}.html', html)
            self.assertIn(part["reference"], html)
            self.assertIn("not a separate Zenodo deposit", html)
            self.assertIn("Creator / responsibility", html)
            self.assertIn("https://doi.org/" + record["doi"], html)
            self.assertIsNotNone(schemas[part["url"]])


if __name__ == "__main__":
    unittest.main()
