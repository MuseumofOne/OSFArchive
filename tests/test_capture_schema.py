from pathlib import Path
import sys, unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from website_metadata import capture_schema


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
            "first_captured_at": "2026-11-05T00:00:00Z",
            "capture": {"captured_at": "2026-11-05T01:00:00Z"},
        }

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
        self.assertEqual(graph["isBasedOn"]["inLanguage"], ["en", "ja"])
        self.assertEqual(graph["encoding"]["sha256"], "b" * 64)
        media = graph["hasPart"][0]
        self.assertEqual(media["@type"], "ImageObject")
        self.assertEqual(media["sha256"], "a" * 64)
        self.assertEqual(media["width"]["value"], 30)
        for field in ["author", "license", "uploadDate", "dateCreated", "duration"]:
            self.assertNotIn(field, media)

    def test_external_and_failed_files_do_not_receive_local_preservation_claims(self):
        graph = capture_schema(
            self.record(),
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


if __name__ == "__main__":
    unittest.main()
