from pathlib import Path
import json, sys, unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from website_metadata import capture_schema, describe
from website_sync import metadata


class CaptureGraph(unittest.TestCase):
    def record(self):
        return {
            "source": {
                "url": "https://www.museumofone.art/essay/",
                "title": "Exact source title",
                "published_at": "2025-01-01",
                "updated_at": None,
                "creators": [{"name": "Credited writer", "role": "Website author"}],
            },
            "summary": "Source summary",
            "language": ["en", "ja"],
            "document_language": {"language": "en-GB", "checked_at": "2026-11-05"},
            "first_captured_at": "2026-11-05T00:00:00Z",
            "capture": {"captured_at": "2026-11-05T01:00:00Z"},
        }

    def test_public_page_citations_survive_both_ghost_head_formats_at_source_scope(self):
        base = self.record()
        url = base["source"]["url"]
        safe = {
            "@type": "CreativeWork", "name": "Archive finding aid",
            "url": "https://archive.example/finding-aid.pdf",
            "publisher": {"@type": "Organization", "name": "Source archive"},
            "encodingFormat": "application/pdf",
        }
        ghost_graph = {"@context": "https://schema.org", "@graph": [
            {"@type": "WebPage", "url": url, "citation": [
                {**safe, "publisher": {**safe["publisher"], "email": "hidden@example.net"}},
                safe,
                {**safe, "url": "https://example.net/unlinked"},
                {**safe, "url": "mailto:private@example.net"},
            ]},
            {"@type": "CreativeWorkSeries", "url": url, "citation": [
                {**safe, "url": "https://example.net/not-page-scope"},
            ]},
            {"@type": "WebPage", "url": url + "different/",
             "citation": [{**safe, "url": "https://example.net/not-page-scope"}]},
        ]}
        body = ('<p><a href="https://archive.example/finding-aid.pdf">Finding aid</a>'
                '<a href="https://example.net/not-page-scope">Related</a>'
                '<a href="mailto:private@example.net">Contact</a></p>')
        for attributes, expect in (
            ('type="application/ld+json"', [safe]),
            ('type="application/json" data-programme-schema-source', [safe]),
            ('type="application/json"', None),
        ):
            with self.subTest(attributes=attributes):
                template = '<script ' + attributes + '>' + json.dumps(ghost_graph) + '</script>'
                source = metadata(dict(base["source"], html=body, codeinjection_head=template), "page")
                self.assertEqual(source.get("source_declared_citations"), expect)
                details = describe(source, "en", "summary", [])
                self.assertEqual(details.get("source_declared_citations"), expect)
                graph = capture_schema(
                    dict(base, source=source, descriptive_metadata=details), [],
                    {"path": "website/source.html.txt", "sha256": "b" * 64, "bytes": 99},
                    "https://archive.museumofone.art/website/web-1.html",
                    "https://archive.museumofone.art",
                )
                self.assertEqual(graph["isBasedOn"].get("citation"), expect)
                self.assertNotIn("citation", graph)

    def test_source_authorship_and_file_fixity_have_distinct_scopes(self):
        asset = {
            "archive_path": "assets/file.png",
            "sha256": "a" * 64,
            "bytes": 42,
            "mime_type": "image/png",
            "availability": "available",
            "url": "https://www.museumofone.art/content/images/file.png",
            "reason": "Original credits and rights remain applicable.",
            "pixel_dimensions": {"width": 30, "height": 40},
        }
        graph = capture_schema(
            self.record(),
            [asset],
            {"path": "website/source.html.txt", "sha256": "b" * 64, "bytes": 99},
            "https://archive.museumofone.art/website/web-1.html",
            "https://archive.museumofone.art",
        )
        self.assertEqual(graph["isBasedOn"]["author"][0]["name"], "Credited writer")
        self.assertNotIn("author", graph)
        self.assertNotIn("dateModified", graph["isBasedOn"])
        self.assertEqual(graph["inLanguage"], "en")
        self.assertEqual(graph["isBasedOn"]["inLanguage"], "en-GB")
        self.assertEqual(graph["isBasedOn"]["mainEntity"]["inLanguage"], ["en", "ja"])
        self.assertEqual(graph["encoding"]["sha256"], "b" * 64)
        media = graph["hasPart"][0]
        self.assertEqual(media["@type"], "ImageObject")
        self.assertEqual(media["sha256"], "a" * 64)
        self.assertEqual(media["width"]["value"], 30)
        for field in ["author", "license", "uploadDate", "dateCreated", "duration"]:
            self.assertNotIn(field, media)

    def test_external_and_failed_files_do_not_receive_local_preservation_claims(self):
        record = self.record()
        record.pop("language")
        graph = capture_schema(
            record,
            [
                {
                    "url": "https://external.example/a.mp3",
                    "availability": "not_checked",
                },
                {"archive_path": "a.pdf", "availability": "failed", "sha256": "a" * 64},
            ],
            {"path": "source.html.txt", "sha256": "b" * 64, "bytes": 0},
            "https://archive.museumofone.art/website/web-1.html",
            "https://archive.museumofone.art",
        )
        self.assertNotIn("hasPart", graph)
        self.assertEqual(graph["isBasedOn"]["inLanguage"], "en-GB")
        self.assertNotIn("mainEntity", graph["isBasedOn"])


if __name__ == "__main__":
    unittest.main()
